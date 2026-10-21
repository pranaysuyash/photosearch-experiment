# Caption→image retrieval — 7174 queries over 7174 images (3503 unique captions; identical-caption images count as one correct set)

| model | dim | device | load_s | images_per_s | queries_per_s | recall@1 | recall@5 | recall@10 | mrr | median_rank | error |
|---|---|---|---|---|---|---|---|---|---|---|---|
| clip-ViT-B-32 | 512 | mps:0 | 5.6 | 65.0 | 110.6 | 0.139 | 0.282 | 0.4 | 0.223 | 22 |  |
