import os
import json
from opsmate.apiserver import api_app

schema = api_app.openapi()


spec_dir = os.path.join("sdk", "spec", "apiserver")
api_file_path = os.path.join(spec_dir, "openapi.json")

os.makedirs(spec_dir, exist_ok=True)

with open(api_file_path, "w") as f:
    json.dump(schema, f, indent=2)
