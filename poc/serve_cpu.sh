#!/bin/bash
# usage: serve_cpu.sh <gguf-name> [port] [parallel-slots] [extra llama-server args...]   (OpenAI API at :port/v1)
T=/root/llm_algo_poc_tools
export LD_LIBRARY_PATH=$T/llama.cpp/build/bin
NP=${3:-8}
exec $T/llama.cpp/build/bin/llama-server -m $T/models/$1 --host 127.0.0.1 --port ${2:-8080} \
  -t 32 -tb 48 -np $NP -c $((NP*6144)) --jinja -a local --no-webui "${@:4}"
