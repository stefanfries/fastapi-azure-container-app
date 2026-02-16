# Technical Requirements

- clean and modulare architecture
- factory patterns where appropriate to enable future extension for new asset classes, new data sources, etc.
- get financial instrument information by scaping the comdirect web page using beautiful soup
- structure parsers for instruments of different asset classes as plugin system
- async code only based on httpx
- strict data validation based o pydantic_v2
- mongo_db as document database
- strict unittests and integration test using pytest
- deploy API to azure container app using github actions

# Current situation

- requirements are partially fulfilled
- a plugin system has been created but only for a limited number of asset classes (stocks and warrants)
- need to complete the plugin system for theother asset classes
- instrument model only contain the structure which is common to all asset classes but not the asset class specific data
- parsers for asset class specific instrument data not implemented yet
- no unittests and no integration tests existing
- base logging structue exists but does not match best practices
- still lots of print statements in the code
- use role model does not exist
- no decision how to implement authentication (develop on our own or use autrh0 for example)
- routes are not protected / authenicated
- 

# Open questions

- how to priorize all the oen tasks
- how to generate a plan to further specify implementation details and prioritize implementation
- what to do first?
    - ensure code quality?
    - refactor to align with pluginsystem to et rif of the legay code for backward compatibility?
    - extend the instrument model to reflect asset class specific information?
    - or what elso?
