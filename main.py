from pydantic import BaseModel, PrivateAttr, computed_field


class User(BaseModel):
    # _name: str = PrivateAttr()
    email: str

    @computed_field
    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str):
        self._name = value


async def main():
    user = User(
        email="john@example.com",
    )
    user.name = "Jane"
    print(user.model_dump())


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
