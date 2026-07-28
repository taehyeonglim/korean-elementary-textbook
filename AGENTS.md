# Local image-prompt workflow

For image-generation prompt requests, use the repository-local `$image-prompt` skill at `.agents/skills/image-prompt`.

- Compile the requested prompt before generating an image.
- Validate high-value prompts with `./scripts/check-image-prompt <prompt-file>` before handing them to ImageGen.
- Keep the upstream toolkit in `vendor/gongnyang-prompt-kit`; update it only with `./scripts/update-gongnyang-prompt-kit`.
