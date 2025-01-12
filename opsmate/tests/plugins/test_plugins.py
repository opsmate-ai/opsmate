import pytest
from os import path

from opsmate.plugins import PluginRegistry


@pytest.fixture
def plugins_dir():
    current_dir = path.dirname(path.abspath(__file__))
    plugins_dir = path.join(current_dir, "fixtures/plugins")
    PluginRegistry.discover(plugins_dir)
    yield
    PluginRegistry.clear()


@pytest.mark.asyncio
async def test_plugin_registry_basic(plugins_dir):
    my_creator = PluginRegistry.get_plugin("my_creator")
    assert my_creator.metadata.description == "you are a LLM"
    assert my_creator.metadata.author == "opsmate"
    assert my_creator.metadata.version == "0.1.0"
    assert my_creator.metadata.source.endswith("fixtures/plugins/essentials.py")

    assert await my_creator.execute(model="gpt-4o-mini") == "openai"
    assert await my_creator.execute(model="claude-3-5-sonnet-20241022") == "anthropic"


@pytest.mark.asyncio
async def test_plugin_registry_override(plugins_dir):
    weather = PluginRegistry.get_plugin("fake_weather")
    assert weather.metadata.name == "fake_weather"
    assert weather.metadata.description == "get the weather"
    assert weather.metadata.author == "opsmate"
    assert weather.metadata.version == "0.1.0"


@pytest.mark.asyncio
async def test_plugin_registy_with_tool(plugins_dir):
    weather = PluginRegistry.get_plugin("fake_weather")
    assert await weather.execute(location="London") == "rainy"
    assert await weather.execute(location="San Francisco") == "sunny"


@pytest.mark.asyncio
async def test_plugin_with_sync_tool(plugins_dir):
    weather = PluginRegistry.get_plugin("fake_weather_sync")
    assert await weather.execute(location="London") == "rainy"
    assert await weather.execute(location="San Francisco") == "sunny"


@pytest.mark.asyncio
async def test_plugin_with_conflicts(plugins_dir):
    current_dir = path.dirname(path.abspath(__file__))
    conflicts_dir = path.join(current_dir, "fixtures/conflicts")
    with pytest.raises(ValueError, match="Plugin my_creator already exists"):
        PluginRegistry.discover(conflicts_dir, ignore_conflicts=False)


@pytest.mark.asyncio
async def test_load_dtools(plugins_dir):
    get_weather = PluginRegistry.get_tool("get_weather")
    assert get_weather is not None
    assert (
        await get_weather(location="London").run()
        == "The location is London. if it's London return raining other wise return sunny"
    )

    assert PluginRegistry.get_tools() == {
        "get_weather": get_weather,
    }
