# 欧亚自驾

2030 年上海出发的欧亚公路环线规划，用 Streamlit 做成可翻页的本地站点。总览看全程，侧栏按国家看停留、路线和地图。

日期是计划，不是边境和签证承诺。

## 行程

2030 年 3 月 1 日从上海出发，9 月 16 日回到上海，约 200 天，全程约 3.4 万公里。

上海 → 霍尔果斯 → 哈萨克斯坦、乌兹别克斯坦 → 俄罗斯南部 → 格鲁吉亚 → 土耳其 → 巴尔干 → 意大利 → 法国、西班牙、葡萄牙 → 英国 → 比利时、荷兰、德国、丹麦 → 冰岛 → 波兰、波罗的海三国 → 西伯利亚、贝加尔湖 → 蒙古 → 二连浩特 → 鄂尔多斯 → 北京 → 上海。

冰岛只在夏天停留，不追极光。芬兰、瑞典、挪威不在这条线上。

预算目标 18.5 万，出发前准备 22 万，预备金 3.5 万。页面上的「吃饭+交通费」只含吃饭、营地、油费、路桥停车和杂费，不含签证、车辆整备和维修。

## 文件

| 文件 | 作用 |
| --- | --- |
| `app.py` | 站点。总览、国家页、地图和图表 |
| `trip_data.py` | 停留、路线、预算和城市介绍。改行程改这里 |
| `欧亚自驾.md` | 同一趟行程的文字稿 |
| `requirements.txt` | Python 依赖 |

站点运行时只读 `app.py` 和 `trip_data.py`。

## 环境

- Python 3.11 或更高
- 依赖：Streamlit、Plotly、pandas、Folium

地图全屏用到 `st.html(..., unsafe_allow_javascript=True)`，需要 Streamlit 1.52 或更高。按下面安装会拿到当前版本，满足这个要求。

## 运行

```bash
cd euroasia
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

浏览器打开终端里给出的地址，默认是 <http://localhost:8501>。
