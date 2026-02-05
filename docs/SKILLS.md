# Skills

Skills are optional tool bundles loaded from the internal root:

```
<internal_root>/skills/<skill_name>/skill.json
```

Example `skill.json`:

```json
{
  "name": "example_skill",
  "description": "Example skill",
  "entrypoint": "skills.example:run"
}
```

Entrypoints should be importable by Python, and the function should accept a single `dict` and return a `dict`. Clawless prepends the `skills` directory to `sys.path`, so modules can be placed directly under `<internal_root>/skills/`.
