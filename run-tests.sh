#!/bin/bash
# Run tests with 1Password credentials injected

# Check if .env.op exists
if [ -f .env.op ]; then
    # Use op inject to inject secrets and run pytest
    op inject -i .env.op -- pytest "$@"
else
    echo "Warning: .env.op not found. Running tests without op inject."
    echo "Create .env.op with 1Password secret references to use op inject."
    pytest "$@"
fi

