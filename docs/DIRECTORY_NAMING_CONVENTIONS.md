# PAKE System - Directory Naming Conventions

## CI-Compatible Directory Naming

To ensure compatibility with case-sensitive filesystems (Linux CI environments), follow these conventions:

### ✅ Recommended Patterns
- Use underscores: `src/services/secrets_manager`
- Use lowercase: `src/services/analytics`
- Use hyphens only for non-Python directories: `docs/api-reference`

### ❌ Avoid These Patterns
- Hyphens in Python package directories: `src/services/secrets-manager`
- Mixed case without clear pattern: `src/services/AgentRuntime`
- Spaces in directory names: `src/services/social media`

### Current Problematic Directories
The following directories use hyphens and may cause import issues on case-sensitive filesystems:

1. `src/services/secrets-manager` → `src/services/secrets_manager`
2. `src/services/agent-runtime` → `src/services/agent_runtime`
3. `src/services/enterprise-integrations` → `src/services/enterprise_integrations`
4. `src/services/social-media-automation` → `src/services/social_media_automation`
5. `src/services/video-generation` → `src/services/video_generation`
6. `src/services/voice-agents` → `src/services/voice_agents`

### Migration Strategy
1. Create new directories with underscore naming
2. Move Python files to new directories
3. Update import statements
4. Update any references in configuration files
5. Test on case-sensitive filesystem

### Testing on Case-Sensitive Filesystem
```bash
# Test imports work correctly
python -c "import src.services.secrets_manager"
python -c "import src.services.agent_runtime"
```

## References
- [Python Package Naming](https://packaging.python.org/en/latest/specifications/name-normalization/)
- [PEP 8 - Style Guide](https://peps.python.org/pep-0008/)
