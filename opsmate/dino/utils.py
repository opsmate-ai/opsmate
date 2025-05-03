from typing import Callable
from inspect import signature
from pydantic import BaseModel as PydanticBaseModel, Field, create_model
from typing import Literal, TypeVar, Any, Optional, List, Dict, Tuple, Type, Union
import structlog

logger = structlog.get_logger(__name__)


def args_dump(fn: Callable, cbk: Callable, args, kwargs):
    """dump the matching args and kwargs from the function to the callback

    Args:
        fn: Source function whose arguments are being passed
        cbk: Callback function to match arguments against
        args: Positional arguments passed to fn
        kwargs: Keyword arguments passed to fn

    Returns:
        Tuple of (matched_args, matched_kwargs) for the callback function

    Example:
    def fn(a, b, c=1, d=2):
        pass

    def cbk(a, d=2):
        pass

    args_dump(fn, cbk, (1, 2), {"c": 3, "d": 4})
    >> ( (1,), {"d": 4})
    """
    fn_params = list(signature(fn).parameters.keys())
    cbk_params = set(signature(cbk).parameters.keys())

    # Match positional arguments
    matched_args = tuple(
        arg for i, arg in enumerate(args) if fn_params[i] in cbk_params
    )

    # Match keyword arguments
    matched_kwargs = {k: v for k, v in kwargs.items() if k in cbk_params}

    return matched_args, matched_kwargs


# Type mapping
JSON_TYPE_MAP: Dict[str, Type] = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    # 'object' and 'array' need special handling
}


def _process_schema_property(
    prop_schema: Dict[str, Any],
    is_required: bool,
    nested_model_name: str,
    definitions: Optional[Dict[str, Any]] = None,
    created_models: Optional[Dict[str, Type[PydanticBaseModel]]] = None,
) -> Tuple[Type, Any]:
    """Processes a single property schema and returns the Python type and Field info."""

    if created_models is None:
        created_models = {}

    # Handle $ref
    if "$ref" in prop_schema:
        ref_path = prop_schema["$ref"]
        if not ref_path.startswith("#/definitions/"):
            logger.warning(
                f"Unsupported $ref format: {ref_path}. Only '#/definitions/' refs are supported."
            )
            # Fallback to Any
            field_type = Any
            default_value = ... if is_required else None
            if not is_required:
                field_type = Optional[field_type]
            return field_type, Field(
                default_value,
                description=prop_schema.get(
                    "description", f"Unsupported $ref: {ref_path}"
                ),
            )

        def_name = ref_path.split("/")[-1]

        if definitions is None or def_name not in definitions:
            logger.warning(f"Definition not found for $ref: {ref_path}")
            # Fallback to Any
            field_type = Any
            default_value = ... if is_required else None
            if not is_required:
                field_type = Optional[field_type]
            return field_type, Field(
                default_value,
                description=prop_schema.get(
                    "description", f"Missing $ref target: {ref_path}"
                ),
            )

        if def_name in created_models:
            model_type = created_models[def_name]
        else:
            # Recursively create model for the definition
            # Prevent infinite recursion by adding placeholder before recursive call
            created_models[def_name] = TypeVar(def_name)  # type: ignore Placeholder
            try:
                model_type = json_schema_to_pydantic_model(
                    definitions[def_name],
                    model_name=def_name,
                    definitions=definitions,
                    created_models=created_models,  # Pass cache
                )
                created_models[def_name] = model_type  # Store in cache
            except Exception as e:
                logger.error(
                    f"Failed to create model for $ref '{def_name}': {e}", exc_info=True
                )
                # Fallback if recursion fails
                model_type = Any  # type: ignore
                created_models[def_name] = model_type  # type: ignore Cache fallback

        field_type = model_type
        default_value = ... if is_required else None
        if not is_required:
            field_type = Optional[field_type]  # type: ignore
        return field_type, Field(
            default_value, description=prop_schema.get("description")
        )

    prop_type = prop_schema.get("type")
    default_value_from_schema = prop_schema.get("default")
    field_description = prop_schema.get("description")
    field_title = prop_schema.get("title")

    python_type: Type = Any
    default_value: Any = ... if is_required else None

    if isinstance(prop_type, list):
        # Handle cases like "type": ["string", "null"] -> Optional[str]
        has_null = "null" in prop_type
        non_null_types = [t for t in prop_type if t != "null"]

        types_in_union = []
        for t in non_null_types:
            if t in JSON_TYPE_MAP:
                types_in_union.append(JSON_TYPE_MAP[t])
            elif t == "object":
                # Nested model - ensure unique name if possible, maybe based on title?
                nested_model = json_schema_to_pydantic_model(
                    prop_schema, nested_model_name, definitions, created_models
                )
                types_in_union.append(nested_model)
            elif t == "array":
                item_schema = prop_schema.get("items", {})
                item_type, _ = _process_schema_property(
                    item_schema,
                    True,
                    f"{nested_model_name}Item",
                    definitions,
                    created_models,
                )
                types_in_union.append(List[item_type])  # type: ignore
            else:
                logger.warning(
                    f"Unknown type '{t}' in type list for property in {nested_model_name}. Using Any."
                )
                types_in_union.append(Any)

        if len(types_in_union) == 1:
            python_type = types_in_union[0]
        elif len(types_in_union) > 1:
            python_type = Union[tuple(types_in_union)]  # type: ignore
        else:  # Only "null" or empty type list?
            python_type = Any  # Fallback

        # Handle optionality
        if has_null or not is_required:
            python_type = Optional[python_type]  # type: ignore
            default_value = None  # Optional implies default None unless overridden
        # If required and no "null" type, default remains ...

    elif prop_type == "object":
        python_type = json_schema_to_pydantic_model(
            prop_schema, nested_model_name, definitions, created_models
        )
        if not is_required:
            python_type = Optional[python_type]
            default_value = None
    elif prop_type == "array":
        item_schema = prop_schema.get("items", {})
        item_type, _ = _process_schema_property(
            item_schema, True, f"{nested_model_name}Item", definitions, created_models
        )
        python_type = List[item_type]  # type: ignore
        if not is_required:
            python_type = Optional[python_type]  # type: ignore
            default_value = None
    elif prop_type in JSON_TYPE_MAP:
        python_type = JSON_TYPE_MAP[prop_type]
        if not is_required:
            python_type = Optional[python_type]
            default_value = None
    elif prop_type is None:
        # No type specified, treat as Any
        logger.debug(
            f"No type specified for property in {nested_model_name}. Using Any."
        )
        python_type = Any
        if not is_required:
            python_type = Optional[python_type]
            default_value = None
    else:
        logger.warning(
            f"Unknown property type '{prop_type}' for property in {nested_model_name}. Using Any."
        )
        python_type = Any
        if not is_required:
            python_type = Optional[python_type]
            default_value = None

    # Override default if specified in schema
    if default_value_from_schema is not None:
        default_value = default_value_from_schema
        # If default is provided, field is implicitly not required for Pydantic initialization
        # But we still need Optional[...] if it *can* be None or wasn't required initially
        if is_required and not str(python_type).startswith("typing.Optional"):
            python_type = Optional[python_type]  # type: ignore

    # Handle enums - overrides previous type assignment
    if "enum" in prop_schema:
        enum_values = tuple(prop_schema["enum"])
        # Check if enum_values is not empty before creating Literal
        if enum_values:
            python_type = Literal[enum_values]  # type: ignore
            if (
                not is_required or None in enum_values
            ):  # If None is a valid enum value, it's optional-like
                python_type = Optional[python_type]  # type: ignore
                if (
                    default_value is ... and default_value_from_schema is None
                ):  # Check if default wasn't set by 'default' or explicit None enum
                    default_value = None
        else:
            logger.warning(f"Empty enum list found in {nested_model_name}. Using Any.")
            python_type = Any
            if not is_required:
                python_type = Optional[python_type]
                default_value = None

    # Create Field object with default and description/title
    field_info = Field(
        default=default_value,
        description=field_description,
        title=field_title,
        # Add other JSON schema constraints like minLength, maxLength, pattern, etc. here if needed
    )

    return python_type, field_info


def json_schema_to_pydantic_model(
    schema: Dict[str, Any],
    model_name: str = "DynamicModel",
    definitions: Optional[Dict[str, Any]] = None,
    created_models: Optional[Dict[str, Type[PydanticBaseModel]]] = None,
) -> Type[PydanticBaseModel]:
    """
    Converts a JSON schema dictionary into a Pydantic model class.

    Args:
        schema: The JSON schema dictionary. Expected to be a valid JSON schema object.
        model_name: The desired name for the generated Pydantic model.
        definitions: Optional dictionary of definitions for resolving $ref (usually from schema's 'definitions' or '$defs').
        created_models: Optional dictionary to cache created models for resolving $ref and handling recursion.

    Returns:
        A dynamically created Pydantic model class inheriting from pydantic.BaseModel.

    Raises:
        ValueError: If the input schema is not a dictionary or is missing 'properties' for an object type.
        TypeError: If conversion fails for unexpected reasons.
    """
    if not isinstance(schema, dict):
        raise ValueError("Input schema must be a dictionary.")

    if created_models is None:
        created_models = {}

    # Use definitions/defs from the schema itself if not provided externally
    if definitions is None:
        definitions = schema.get(
            "definitions", schema.get("$defs")
        )  # Support both 'definitions' and '$defs'

    # Handle simple cases first (e.g. schema is just {"type": "string"})
    if "type" in schema and schema["type"] != "object" and "properties" not in schema:
        # If the top-level schema is not an object, we can't directly make a model.
        # This function expects an object schema to create a model with fields.
        # A caller might handle this by wrapping it, but this func creates models from object schemas.
        raise ValueError(
            f"Schema for '{model_name}' is not an object type schema; cannot create Pydantic model directly."
        )

    # If it's an object schema but has no properties, create an empty model
    properties = schema.get("properties", {})
    required = set(schema.get("required", []))
    field_definitions = {}

    for prop_name, prop_schema in properties.items():
        # Sanitize property name to be a valid Python identifier if necessary
        # For simplicity, assume valid identifiers for now. Add sanitization later if needed.
        sanitized_prop_name = prop_name  # Placeholder for potential sanitization

        is_req = prop_name in required
        try:
            field_type, field_info = _process_schema_property(
                prop_schema,
                is_req,
                f"{model_name}_{sanitized_prop_name}",  # Pass sanitized name for nesting
                definitions=definitions,
                created_models=created_models,
            )
            field_definitions[sanitized_prop_name] = (field_type, field_info)

        except Exception as e:
            logger.error(
                f"Failed to process property '{prop_name}' in model '{model_name}': {e}",
                exc_info=True,
            )
            # Fallback: Add as Any type with error description
            field_type = Any
            field_default = None if not is_req else ...
            field_info = Field(
                default=field_default, description=f"Failed to parse schema: {e}"
            )
            field_definitions[sanitized_prop_name] = (field_type, field_info)

    # Create the model using field definitions
    try:
        model = create_model(
            model_name, __base__=PydanticBaseModel, **field_definitions
        )
    except Exception as e:
        logger.error(
            f"Failed to create Pydantic model '{model_name}': {e}", exc_info=True
        )
        raise TypeError(
            f"Could not create Pydantic model '{model_name}' from schema."
        ) from e

    # Add model description (docstring) if present in schema
    if "description" in schema:
        model.__doc__ = schema["description"]

    # Store the fully created model in the cache, replacing any placeholders
    # This check is important if called recursively for definitions
    if definitions and model_name in definitions:
        created_models[model_name] = model

    return model
