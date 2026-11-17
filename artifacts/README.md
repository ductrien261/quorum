# Model artifacts

Thư mục `artifacts/vn/` chứa trọng số và tham số chuẩn hoá xuất từ notebook Kaggle
`midmoe-vn-transfer-weights` (file `midmoe_vn_artifacts.zip`). Không commit thư mục này lên GitHub.

Cấu trúc cần có:

```
artifacts/vn/
├── model_config.json
├── vn_tickers_sorted.json
├── vn_feature_order.json
├── vn_norm_params.json
├── vn_sector_graph.npy
├── icb_industry.csv
├── vn_parity_ref.npz      # để chạy test tương đương
├── vn_test_cube.npz       # để nạp lịch sử kiểm định 2025
└── weights/model_seed0.pt … model_seed9.pt
```

Cách lấy: mở notebook trên Kaggle, tab Output, tải `midmoe_vn_artifacts.zip`, giải nén vào `artifacts/vn/`.
