#!/bin/bash
# Run lambda_handler directly with 1Password credentials injected

# Check if .env.op exists
if [ -f .env.op ]; then
    # Use op run to inject secrets as environment variables and run the lambda handler script
    op run --env-file=.env.op -- python run_lambda_handler.py "$@"
else
    echo "Warning: .env.op not found. Running without op run."
    echo "Create .env.op with 1Password secret references to use op run."
    python run_lambda_handler.py "$@"
fi

