#!/bin/bash
# DocBro environment wrapper script
# This script sets the correct environment variables for DocBro

export DOCBRO_REDIS_URL=redis://localhost:6380
export DOCBRO_QDRANT_URL=http://localhost:6333

# Run docbro with all arguments passed to this script
docbro "$@"