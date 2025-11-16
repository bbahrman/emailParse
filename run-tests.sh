#!/bin/bash
# Run tests with 1Password credentials injected

# Check if .env.op exists
if [ -f .env.op ]; then
    # Use op run to inject secrets as environment variables and run pytest
    op run --env-file=.env.op -- pytest "$@"
else
    echo "Warning: .env.op not found. Running tests without op run."
    echo "Create .env.op with 1Password secret references to use op run."
    pytest "$@"
fi

