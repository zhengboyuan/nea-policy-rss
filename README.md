# 国家能源局最新文件 RSS

非官方公开文件订阅源；仅包含公开网站的列表数据和采集代码。

订阅地址：https://raw.githubusercontent.com/zhengboyuan/nea-policy-rss/main/public/feed.xml

来源：https://www.nea.gov.cn/policy/zxwj.htm

每六小时由 GitHub Actions 尝试更新。自动识别栏目所用的公开 JSON 文件，收录其全部记录，按原文链接去重。保留已采集的历史记录，源站删除或移出列表的记录不随之删除。抓取失败不会发布残缺或空订阅。

首次采集的官网列表包含 1,000 条记录（界面每页 25 条，共 40 页），去重后为 999 条。这个范围是官网目前公开提供的列表，不代表该栏目自创办以来所有文件；列表中有少数较早年份的记录，日期跨度不等于连续覆盖所有年份。

每条包含完整列表标题、真实发布时间、唯一原文链接、源站摘要（若有）。正文及附件通过原文链接访问，本项目不下载保存所有正文和附件。不同阅读器对历史条目的导入策略可能不同。

运行：安装 requirements.txt 后执行 `python collect.py`。

输出：`data/notices.json`、`public/feed.xml`、`public/status.json`。
