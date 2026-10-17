import json
from pathlib import Path
from jsonschema import Draft202012Validator,FormatChecker
from waypoint.demo import fixture
root=Path(__file__).resolve().parents[1]

def test_schemas_match_authored_fixture():
    plan,events=fixture()
    for name,items in [('plan.schema.json',[plan]),('event.schema.json',events)]:
        schema=json.loads((root/'schemas'/name).read_text());Draft202012Validator.check_schema(schema)
        validator=Draft202012Validator(schema,format_checker=FormatChecker())
        for item in items:validator.validate(item)

def test_public_routes_cannot_control_agents():
    spec=json.loads((root/'schemas/openapi.json').read_text())
    assert not any(any(word in path for word in ['start-agent','resume','approval','steer']) for path in spec['paths'])
