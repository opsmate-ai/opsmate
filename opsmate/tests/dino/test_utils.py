import pytest

from opsmate.dino.utils import args_dump, json_schema_to_pydantic_model
from pydantic import BaseModel as PydanticBaseModel, ValidationError
from typing import Optional, List, Union, Literal


def test_args_dump():
    def fn(a, b, c=1, d=2):
        pass

    def cbk(a, d=2):
        pass

    assert args_dump(fn, cbk, (1, 2), {"c": 3, "d": 4}) == ((1,), {"d": 4})


def test_args_dump_with_unmatching():
    def fn(a, b, c=1, d=2):
        pass

    def cbk(a, d=2, e=3):
        pass

    assert args_dump(fn, cbk, (1, 2), {"c": 3, "d": 4}) == ((1,), {"d": 4})


@pytest.mark.asyncio
async def test_args_dump_async():
    async def fn(a, b, c=1, d=2):
        pass

    async def cbk(a, d=2):
        pass

    assert args_dump(fn, cbk, (1, 2), {"c": 3, "d": 4}) == ((1,), {"d": 4})


@pytest.mark.asyncio
async def test_args_dump_async_to_sync_with_kwargs():
    async def fn(a, b, c=1, d=2):
        pass

    def cbk(a, d=2):
        pass

    assert args_dump(fn, cbk, (1, 2), {"c": 3, "d": 4}) == ((1,), {"d": 4})


def test_args_dump_sync_to_async_with_kwargs():
    def fn(a, b, c=1, d=2):
        pass

    async def cbk(a, d=2):
        pass

    assert args_dump(fn, cbk, (1, 2), {"c": 3, "d": 4}) == ((1,), {"d": 4})


def test_basic_types():
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "User name"},
            "age": {"type": "integer"},
            "height": {"type": "number"},
            "is_active": {"type": "boolean"},
        },
        "required": ["name", "age"],
        "description": "Basic user model",
    }
    Model = json_schema_to_pydantic_model(schema, "UserModel")

    assert issubclass(Model, PydanticBaseModel)
    assert Model.__name__ == "UserModel"
    assert Model.__doc__ == "Basic user model"

    fields = Model.model_fields
    assert "name" in fields
    assert fields["name"].annotation == str
    assert fields["name"].is_required() is True
    assert fields["name"].description == "User name"

    assert "age" in fields
    assert fields["age"].annotation == int
    assert fields["age"].is_required() is True

    assert "height" in fields
    assert fields["height"].annotation == Optional[float]
    assert fields["height"].is_required() is False
    assert fields["height"].default is None

    assert "is_active" in fields
    assert fields["is_active"].annotation == Optional[bool]
    assert fields["is_active"].is_required() is False
    assert fields["is_active"].default is None

    # Test instantiation
    instance = Model(name="Alice", age=30, height=5.5)
    assert instance.name == "Alice"
    assert instance.age == 30
    assert instance.height == 5.5
    assert instance.is_active is None

    with pytest.raises(ValidationError):
        Model(name="Bob")  # Missing age


def test_default_values():
    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "default": "pending"},
            "count": {"type": "integer", "default": 0},
        },
    }
    Model = json_schema_to_pydantic_model(schema, "StatusModel")

    fields = Model.model_fields
    assert fields["status"].annotation == Optional[str]
    assert fields["status"].default == "pending"
    assert fields["status"].is_required() is False

    assert fields["count"].annotation == Optional[int]
    assert fields["count"].default == 0
    assert fields["count"].is_required() is False

    instance = Model()
    assert instance.status == "pending"
    assert instance.count == 0

    instance2 = Model(status="active")
    assert instance2.status == "active"
    assert instance2.count == 0


def test_nested_object():
    schema = {
        "type": "object",
        "properties": {
            "user": {
                "type": "object",
                "properties": {"id": {"type": "integer"}, "email": {"type": "string"}},
                "required": ["id"],
            }
        },
        "required": ["user"],
    }
    Model = json_schema_to_pydantic_model(schema, "OuterModel")

    fields = Model.model_fields
    assert "user" in fields
    assert fields["user"].is_required() is True
    assert issubclass(fields["user"].annotation, PydanticBaseModel)
    assert fields["user"].annotation.__name__ == "OuterModel_user"

    NestedModel = fields["user"].annotation
    nested_fields = NestedModel.model_fields
    assert "id" in nested_fields
    assert nested_fields["id"].annotation == int
    assert nested_fields["id"].is_required() is True

    assert "email" in nested_fields
    assert nested_fields["email"].annotation == Optional[str]
    assert nested_fields["email"].is_required() is False

    # Test instantiation
    instance = Model(user={"id": 123, "email": "test@example.com"})
    assert instance.user.id == 123
    assert instance.user.email == "test@example.com"

    instance2 = Model(user={"id": 456})
    assert instance2.user.id == 456
    assert instance2.user.email is None

    with pytest.raises(ValidationError):
        Model(user={"email": "fail@example.com"})  # missing id in nested

    with pytest.raises(ValidationError):
        Model()  # missing user


def test_array_types():
    schema = {
        "type": "object",
        "properties": {
            "tags": {"type": "array", "items": {"type": "string"}},
            "scores": {"type": "array", "items": {"type": "integer"}},
            "coordinates": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"x": {"type": "number"}, "y": {"type": "number"}},
                    "required": ["x", "y"],
                },
            },
        },
    }
    Model = json_schema_to_pydantic_model(schema, "ArrayModel")

    fields = Model.model_fields
    assert "tags" in fields
    assert fields["tags"].annotation == Optional[List[str]]
    assert fields["tags"].is_required() is False

    assert "scores" in fields
    assert fields["scores"].annotation == Optional[List[int]]
    assert fields["scores"].is_required() is False

    assert "coordinates" in fields
    assert (
        str(fields["coordinates"].annotation)
        == "typing.Optional[typing.List[opsmate.dino.utils.ArrayModel_coordinatesItem]]"
    )
    # get to ArrayModel_coordinatesItem
    CoordModel = fields["coordinates"].annotation.__args__[0].__args__[0]
    print(CoordModel)
    assert issubclass(CoordModel, PydanticBaseModel)
    assert CoordModel.__name__ == "ArrayModel_coordinatesItem"
    assert CoordModel.model_fields["x"].annotation == float
    assert CoordModel.model_fields["y"].annotation == float
    assert CoordModel.model_fields["x"].is_required() is True
    assert CoordModel.model_fields["y"].is_required() is True

    # Test instantiation
    instance = Model(
        tags=["a", "b"],
        scores=[1, 2],
        coordinates=[{"x": 1.0, "y": 2.0}, {"x": 3.0, "y": 4.0}],
    )
    assert instance.tags == ["a", "b"]
    assert instance.scores == [1, 2]
    assert len(instance.coordinates) == 2
    assert instance.coordinates[0].x == 1.0
    assert instance.coordinates[1].y == 4.0

    instance2 = Model()
    assert instance2.tags is None
    assert instance2.scores is None
    assert instance2.coordinates is None

    with pytest.raises(ValidationError):  # Wrong item type
        Model(tags=[1, 2])

    with pytest.raises(ValidationError):  # Missing required field in array object item
        Model(coordinates=[{"x": 1.0}])


def test_enum_type():
    schema = {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "enum": [
                    "pending",
                    "running",
                    "failed",
                    "success",
                    None,
                ],  # Including None makes it Optional
            },
            "required_choice": {"type": "string", "enum": ["A", "B", "C"]},
        },
        "required": ["required_choice"],
    }
    Model = json_schema_to_pydantic_model(schema, "EnumModel")

    fields = Model.model_fields
    assert "status" in fields
    # The Literal type is one of the args in the Union
    assert fields["status"].annotation.__origin__ is Union  # Optional is Union[T, None]
    literal_type = None
    none_type = type(None)
    for arg in fields["status"].annotation.__args__:
        if arg is not none_type:
            literal_type = arg
            break
    assert getattr(literal_type, "__origin__", None) is Literal
    assert set(literal_type.__args__) == {  # type: ignore
        "pending",
        "running",
        "failed",
        "success",
        None,  # None IS included in the Literal args here
    }

    assert fields["status"].is_required() is False
    assert (
        fields["status"].default is None
    )  # None in enum implies optional default None

    assert "required_choice" in fields
    assert fields["required_choice"].annotation.__origin__ is Literal
    assert set(fields["required_choice"].annotation.__args__) == {"A", "B", "C"}
    assert fields["required_choice"].is_required() is True

    # Test instantiation
    instance = Model(status="running", required_choice="A")
    assert instance.status == "running"
    assert instance.required_choice == "A"

    instance2 = Model(required_choice="B", status=None)
    assert instance2.status is None
    assert instance2.required_choice == "B"

    instance3 = Model(required_choice="C")  # Optional status defaults to None
    assert instance3.status is None
    assert instance3.required_choice == "C"

    with pytest.raises(ValidationError):  # Invalid enum value
        Model(status="unknown", required_choice="A")

    with pytest.raises(ValidationError):  # Missing required enum
        Model(status="pending")


def test_union_types():
    schema = {
        "type": "object",
        "properties": {
            "id": {"type": ["string", "integer"]},
            "value": {"type": ["number", "null"]},  # Should become Optional[float]
            "mixed_list": {"type": "array", "items": {"type": ["string", "boolean"]}},
        },
        "required": ["id"],
    }
    Model = json_schema_to_pydantic_model(schema, "UnionModel")

    fields = Model.model_fields
    assert "id" in fields
    # Union order might vary, check elements
    assert fields["id"].annotation.__origin__ is Union
    assert set(fields["id"].annotation.__args__) == {str, int}
    assert fields["id"].is_required() is True

    assert "value" in fields
    assert fields["value"].annotation == Optional[float]
    assert fields["value"].is_required() is False

    assert "mixed_list" in fields
    assert (
        fields["mixed_list"].annotation.__origin__ is Union
    )  # Optional[List[...]] -> Union[List[...], None]
    list_type = fields["mixed_list"].annotation.__args__[0]  # Get List[...]
    assert list_type.__origin__ == list
    ListItemType = list_type.__args__[0]  # Get Union[str, bool]
    assert ListItemType.__origin__ is Union
    assert set(ListItemType.__args__) == {str, bool}

    # Test instantiation
    instance_str = Model(id="abc", value=1.2, mixed_list=["hello", True, "world"])
    assert instance_str.id == "abc"
    assert instance_str.value == 1.2
    assert instance_str.mixed_list == ["hello", True, "world"]

    instance_int = Model(id=123, mixed_list=[False, "test"])
    assert instance_int.id == 123
    assert instance_int.value is None
    assert instance_int.mixed_list == [False, "test"]

    with pytest.raises(ValidationError):
        Model(id=None)  # Required field

    with pytest.raises(ValidationError):
        Model(id="abc", value="not a float")

    with pytest.raises(ValidationError):
        Model(id="abc", mixed_list=[123])  # Wrong type in list


def test_ref_definitions():
    schema = {
        "type": "object",
        "properties": {
            "main_prop": {"$ref": "#/definitions/Address"},
            "alt_prop": {"$ref": "#/definitions/Address"},
        },
        "required": ["main_prop"],
        "definitions": {
            "Address": {
                "type": "object",
                "properties": {
                    "street": {"type": "string"},
                    "city": {"type": "string", "default": "Unknown"},
                },
                "required": ["street"],
            }
        },
    }
    Model = json_schema_to_pydantic_model(schema, "RefModel")

    fields = Model.model_fields
    assert "main_prop" in fields
    assert fields["main_prop"].is_required() is True
    assert issubclass(fields["main_prop"].annotation, PydanticBaseModel)
    assert fields["main_prop"].annotation.__name__ == "Address"

    assert "alt_prop" in fields
    assert fields["alt_prop"].is_required() is False
    # Optional[Address] -> Union[Address, None]
    assert fields["alt_prop"].annotation.__origin__ is Union
    address_type_in_union = fields["alt_prop"].annotation.__args__[0]
    assert issubclass(address_type_in_union, PydanticBaseModel)
    assert address_type_in_union.__name__ == "Address"

    # Check the definition model itself
    AddressModel = fields["main_prop"].annotation
    addr_fields = AddressModel.model_fields
    assert "street" in addr_fields
    assert addr_fields["street"].annotation == str
    assert addr_fields["street"].is_required() is True

    assert "city" in addr_fields
    assert addr_fields["city"].annotation == Optional[str]
    assert addr_fields["city"].default == "Unknown"
    assert addr_fields["city"].is_required() is False

    # Test instantiation
    addr_data = {"street": "123 Main St"}
    instance = Model(
        main_prop=addr_data, alt_prop={"street": "456 Side St", "city": "Exampleville"}
    )
    assert instance.main_prop.street == "123 Main St"
    assert instance.main_prop.city == "Unknown"  # Default applied
    assert instance.alt_prop.street == "456 Side St"
    assert instance.alt_prop.city == "Exampleville"

    instance2 = Model(main_prop={"street": "789 Road"})  # Optional alt_prop is None
    assert instance2.main_prop.street == "789 Road"
    assert instance2.main_prop.city == "Unknown"
    assert instance2.alt_prop is None

    with pytest.raises(ValidationError):  # Missing required street in main_prop
        Model(main_prop={"city": "No Street"})

    with pytest.raises(ValidationError):  # Missing main_prop
        Model()


def test_empty_object():
    schema = {"type": "object", "properties": {}}
    Model = json_schema_to_pydantic_model(schema, "EmptyModel")
    assert issubclass(Model, PydanticBaseModel)
    assert not Model.model_fields  # No fields

    instance = Model()
    assert instance.model_dump() == {}


def test_invalid_schema_input():
    with pytest.raises(ValueError, match="Input schema must be a dictionary."):
        json_schema_to_pydantic_model(None)  # type: ignore

    with pytest.raises(ValueError, match="Input schema must be a dictionary."):
        json_schema_to_pydantic_model([])  # type: ignore

    with pytest.raises(
        ValueError,
        match="not an object type schema; cannot create Pydantic model directly.",
    ):
        json_schema_to_pydantic_model({"type": "string"}, "NotObjectModel")
