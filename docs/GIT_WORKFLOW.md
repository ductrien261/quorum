# Quy trình git cho Quorum

Tài liệu này có hai phần:

1. **Đưa code lần đầu lên GitHub:** chạy một script, để máy tự tạo repo, 15 issue, 15 nhánh, 50 commit và 15 pull request (đã merge).
2. **Làm tính năng mới về sau:** các bước làm tay theo cùng quy ước.

## Chuẩn bị (làm một lần)

1. Cài **Git for Windows**: https://git-scm.com/download/win (cài kèm Git Bash).
2. Cài **GitHub CLI**: https://cli.github.com, hoặc chạy `winget install --id GitHub.cli` trong PowerShell.
3. Mở terminal mới và kiểm tra:

   ```powershell
   git --version
   gh --version
   ```

4. Khai báo tên và email cho commit. Email nên trùng email tài khoản GitHub để commit hiện avatar của bạn:

   ```powershell
   git config --global user.name "Nguyen Duc Trien"
   git config --global user.email "email-github-cua-ban@example.com"
   ```

5. Đăng nhập GitHub CLI, chọn `GitHub.com` → `HTTPS` → `Login with a web browser`:

   ```powershell
   gh auth login
   ```

## Phần 1: đưa toàn bộ code lên GitHub bằng một lệnh

Trong thư mục `quorum` (chưa có thư mục `.git` cũng được):

### Cách thường dùng: tự tạo repo và liên kết, script lo issue/commit/PR

1. Vào https://github.com/new, đặt tên `quorum`, chọn Private. **Không tick** "Add a README", không chọn .gitignore
   hay license, để repo trống. Bấm *Create repository* rồi copy link `https://github.com/<tên>/quorum.git`.
2. Trong thư mục `quorum`, liên kết repo (chưa `git add`, chưa commit gì):

   ```powershell
   git init
   git branch -M main
   git remote add origin https://github.com/<tên>/quorum.git
   git remote -v
   ```

3. Chạy script. Nó thấy `origin` đã có nên không tạo repo mới, chỉ commit, đẩy, tạo issue và PR:

   ```powershell
   python scripts/publish_history.py
   ```

Script dừng và báo lỗi nếu repo GitHub không trống hoặc bạn đã lỡ commit cả thư mục. Khi đó xoá thư mục `.git` (và tạo
lại repo trống nếu cần) rồi làm lại từ bước 2.

### Cách nhanh: để script tạo luôn repo

```powershell
python scripts/publish_history.py --dry-run         # xem trước 15 issue / PR và các commit, chưa chạy gì
python scripts/publish_history.py --repo quorum     # chạy thật, repo riêng tư
```

Tuỳ chọn:

| Tham số | Ý nghĩa |
| --- | --- |
| `--repo quorum` | Tên repo sẽ tạo trên GitHub |
| `--owner ten-to-chuc` | Tạo repo dưới tổ chức hoặc tài khoản khác (ví dụ tài khoản của bạn cùng nhóm, nếu bạn có quyền) |
| `--public` | Tạo repo công khai thay vì riêng tư |
| `--delay 3` | Số giây nghỉ giữa các bước gọi GitHub (tăng lên nếu gặp lỗi giới hạn tần suất) |

Script làm theo thứ tự:

1. `git init`, commit `.gitignore`, tạo repo trên GitHub, đẩy nhánh `main`, tạo nhãn (`ml`, `data`, `backend`, `assistant`, `frontend`, `docs`, `setup`).
2. Với mỗi tính năng (15 tính năng, xem `--dry-run`):
   * tạo **issue** mô tả việc cần làm;
   * tạo **nhánh** `feat/<tên>` từ `main`;
   * **commit** từng phần nhỏ (ví dụ `feat(ml): technical indicators and normalisation`);
   * đẩy nhánh, mở **pull request** có dòng `Closes #<số issue>`;
   * **merge** PR (issue tự đóng), xoá nhánh, quay về `main`.
3. In ra link repo và báo nếu còn file nào chưa nằm trong commit.

Thời gian chạy khoảng 10-15 phút, không cần thao tác gì thêm. Nếu mất mạng hay tắt máy giữa chừng, chạy lại **đúng lệnh cũ**:
tiến độ được lưu trong `.git/publish_state.json`, các bước đã xong sẽ được bỏ qua.

Một số đảm bảo của script:

* Commit message chỉ gồm đúng dòng mô tả, **không có dòng `Co-authored-by`** hay chữ ký nào khác. Script chạy commit với
  `--no-verify` và tắt `commit.template` để hook hay template trên máy không chèn thêm gì.
* Không commit `.env`, cơ sở dữ liệu (`data/`) hay trọng số mô hình (`artifacts/vn/`). Script dừng lại nếu `artifacts/vn`
  không nằm trong `.gitignore`.
* Tác giả commit là tên/email bạn cấu hình ở bước 4.

**Nhóm 2 người:** người còn lại vào repo trên GitHub, chọn *Settings → Collaborators → Add people* để được mời, rồi
`git clone` về máy. Từ đó cả hai làm theo Phần 2.

## Phần 2: làm một tính năng mới

Ví dụ thêm cảnh báo qua email khi mã trong danh sách theo dõi vào top 5.

```powershell
# 1. Tạo issue (hoặc tạo trên web GitHub)
gh issue create --title "Cảnh báo email khi mã theo dõi vào top 5" --body "Gửi email lúc 17:00 nếu..." --label backend

# 2. Cập nhật main và tạo nhánh
git checkout main
git pull
git checkout -b feat/watchlist-alerts

# 3. Code, rồi commit từng phần nhỏ, mỗi commit một ý
git add backend/app/services/alerts.py
git commit -m "feat(alerts): find watched tickers that entered the top 5"
git add backend/app/pipeline/scheduler.py
git commit -m "feat(alerts): send the alert email after the daily job"

# 4. Đẩy nhánh và mở pull request, ghi số issue để tự đóng khi merge
git push -u origin feat/watchlist-alerts
gh pr create --title "Cảnh báo email khi mã theo dõi vào top 5" --body "Closes #15"

# 5. Bạn cùng nhóm xem và duyệt trên GitHub (Files changed → Review changes → Approve), rồi merge
gh pr merge --merge --delete-branch
git checkout main
git pull
```

### Quy ước commit message

Viết tiếng Anh, thể mệnh lệnh, chữ thường, không dấu chấm cuối, tối đa khoảng 72 ký tự:

```
<loại>(<phạm vi>): <mô tả ngắn>
```

| Loại | Dùng khi |
| --- | --- |
| `feat` | Thêm tính năng |
| `fix` | Sửa lỗi |
| `docs` | Chỉ sửa tài liệu |
| `test` | Thêm hoặc sửa test |
| `refactor` | Sửa cấu trúc code, không đổi hành vi |
| `chore` | Cấu hình, thư viện, việc lặt vặt |

Phạm vi thường dùng: `ml`, `data`, `pipeline`, `api`, `assistant`, `web`, `brand`.

### Quy ước tên nhánh

`feat/<tên-ngắn>`, `fix/<tên-ngắn>`, `docs/<tên-ngắn>`, viết thường, nối bằng gạch ngang.

### Trước khi mở pull request

```powershell
cd backend;  python -m pytest
cd frontend; npm run build
```
