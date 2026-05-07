# V2.4 Hotfix — Social platform status endpoint

Fixes the `/api/social-platforms/status` endpoint by serializing the slotted `LastfmStatus` dataclass with `dataclasses.asdict()` instead of `__dict__`.

Validation:

```powershell
cd backend
pytest tests/test_api_v2_social_platforms.py
pytest
```
