# 模型部署

## Embedding模型
```shell
vllm serve /mnt/nvme0n1p1/models/Qwen/Qwen3-Embedding-0.6B \
  --host 0.0.0.0 \
  --port PORT \
  --disable-log-stats \
  --served-model-name Qwen3-Embedding-0.6B > logs/vllm/Qwen3-Embedding-0.6B.log 2>&1 &
```

## Reranker模型
```shell
# qwen3-reranker
vllm serve /mnt/nvme0n1p1/models/Qwen/Qwen3-Reranker-0.6B \
  --host 0.0.0.0 \
  --port PORT \
  --task score \
  --hf_overrides '{"architectures": ["Qwen3ForSequenceClassification"],"classifier_from_token": ["no", "yes"],"is_original_qwen3_reranker": true}' \
  --disable-log-stats \
  --served-model-name Qwen3-Reranker-0.6B > logs/vllm/Qwen3-Reranker-0.6B.log 2>&1 &
  
# bge-m3-reranker
vllm serve /mnt/nvme0n1p1/models/BAAI/bge-reranker-v2-m3 \
   --host 0.0.0.0 \
   --port PORT \
   --task score \
   --disable-log-stats \
   --served-model-name bge-reranker-v2-m3 > logs/vllm/bge-reranker-v2-m3.log 2>&1 &
```

## LLM 模型
```shell
vllm serve /mnt/nvme0n1p1/models/Qwen/Qwen3-30B-A3B-Instruct-2507 \
   --host 0.0.0.0 \
   --port PORT \
   --tensor-parallel-size 2 \
   --disable-log-stats \
   --enable-auto-tool-choice \
   --tool-call-parser hermes \
   --served-model-name Qwen3-30B-A3B-Instruct-2507 > logs/vllm/Qwen3-30B-A3B-Instruct-2507.log 2>&1 &
```