

# 1. 初始化 git 仓库
git init

# 2. 将所有文件添加到暂存区（.gitignore 会自动帮你过滤掉 .venv 等不需要上传的临时文件）
git add .

# 3. 提交本地 commit
git commit -m "feat: initial release of Say-Do-Gap-Project v1.0 with LLM Say-Do Gap dashboard"

# 4. 重命名默认分支为主分支 main
git branch -M main

# 5. 关联你的 GitHub 远程仓库（把下面链接换成你自己在 GitHub 上新建的空仓库地址）
git remote add origin  https://github.com/Sola1004/Say-Do-Gap-Project-v1.0
https://github.com/Sola1004/Say-Do-Gap-Project.git 
# 6. 推送上去！
git push -u origin main

# 1. 精准、逐个将这五个超标的 CSV 文件从 Git 追踪中强制移除
git rm --cached "data/raw/quantitative_market/按行业分类的股票投资组合文件/Fund_IndustryStockClass.csv"
git rm --cached "data/raw/quantitative_market/按行业分类的股票投资组合文件/Fund_IndustryStockClass1.csv"
git rm --cached "data/raw/quantitative_market/按行业分类的股票投资组合文件/Fund_IndustryStockClass2.csv"
git rm --cached "data/raw/quantitative_market/按行业分类的股票投资组合文件/Fund_IndustryStockClass3.csv"
git rm --cached "data/raw/quantitative_market/按行业分类的股票投资组合文件/Fund_IndustryStockClass4.csv"

# 2. 确保把打包好的压缩包加回 Git 追踪
git add "/Users/solaartemis/Say-Do-Gap-Project/data/raw/quantitative_market/按行业分类的股票投资组合文件.zip"

# 3. 提交这次干净的清理
git commit -m "fix: remove heavy raw csv files explicitly and keep zip archive"

# 4. 稳稳推送到远程仓库
git push -u origin main