import streamlit as st
import re
import asyncio
from google import genai
from google.genai import types
import datetime

# --- 1. 页面基础配置 ---
st.set_page_config(page_title="Crypto 信息收集助手", page_icon="🕵️", layout="wide")

st.title("🕵️ Crypto 信息收集助手")
st.caption("由 Gemini 2.5 & Google Search 提供支持 | 多标的分析模式")

# --- 2. 侧边栏配置 ---
with st.sidebar:
    st.header("⚙️ 设置")
    api_key = st.text_input("Gemini API Key", type="password", help="在此输入你的 Google AI Studio Key")    
    st.markdown("---")
    st.markdown("### 📅 时间范围")
    # 增加时间选择器
    time_range = st.selectbox(
        "选择回溯时间",
        options=["过去 24 小时", "过去 3 天", "过去 7 天", "过去 30 天"],
        index=2 # 默认选7天
    )
    
    st.markdown("### 🎯 研究标的")
    # 增加标的输入框，默认给几个例子
    assets_input = st.text_input(
        "输入代币名称 (用逗号分隔)", 
        value="BTC, ETH, AAVE",
        placeholder="例如: BTC, SOL, PEPE"
    )

# --- 3. 核心逻辑函数 ---
def get_asset_report(client, asset, time_str):
    """
    针对单个标的调用 Gemini 进行联网搜索和总结
    """
    today = datetime.date.today().strftime("%Y-%m-%d")
    
    prompt = f"""
    今天是 {today}。
    请利用 Google Search 搜索关于 **{asset}** 在 **{time_str}** 的重要新闻、链上数据变动和市场分析。

    请严格按照以下要求生成中文简报：
    1. **标题**：使用 Emoji 开头，例如 "🪙 BTC 市场情报"。
    2. **核心摘要**：一句话总结该标的这段时间的整体表现（看涨/看跌/震荡）。
    3. **情报列表**：
       - 请列出最重要的市场动态，**按重要程度降序排列**。
       - **数量限制**：最多输出 15 条，少于 15 条则列出实际数量。
       - 每条格式：【时间/来源】+ 新闻内容 + (对价格的影响分析)。
    
    请确保信息来源真实，去除重复信息。
    """

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash', # 确保使用支持搜索的模型
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                response_modalities=["TEXT"]
            )
        )
        return response
    except Exception as e:
        return f"Error: {str(e)}"

async def get_asset_report_async(client, asset, time_str):
    return await asyncio.to_thread(get_asset_report, client, asset, time_str)

# --- 4. 主界面交互 ---
if st.button("🚀 开始搜集情报", type="primary"):
    if not api_key:
        st.error("请先在左侧侧边栏输入 API Key！")
    else:
        # 处理用户输入的标的字符串，分割成列表
        # 例如 "BTC, ETH,  AAVE " -> ['BTC', 'ETH', 'AAVE']
        assets_list = [x.strip().upper() for x in assets_input.split(',') if x.strip()]

        if not assets_list:
            st.warning("请输入至少一个标的。")
        else:
            try:
                client = genai.Client(api_key=api_key)
                
                # 创建一个状态容器，显示进度
                status_container = st.status("正在启动 AI 研究员...", expanded=True)
                
                async def run_analysis():
                    tasks = []
                    for asset in assets_list:
                        status_container.write(f"🔍 正在准备搜索 {asset} 的数据...")
                        tasks.append(get_asset_report_async(client, asset, time_range))
                    return await asyncio.gather(*tasks)

                # 运行异步任务
                results = asyncio.run(run_analysis())
                
                # 循环展示结果
                for i, asset in enumerate(assets_list):
                    response = results[i]
                    
                    # 结果展示区 - 使用 expander 折叠框，让界面更整洁
                    with st.expander(f"📊 {asset} 近期信息总结", expanded=True):
                        if isinstance(response, str) and "Error" in response:
                            st.error(f"搜索 {asset} 时发生错误: {response}")
                        elif hasattr(response, 'text'):
                            st.markdown(response.text)
                            
                            # 显示来源链接 (如果有)
                            if response.candidates and response.candidates[0].grounding_metadata:
                                metadata = response.candidates[0].grounding_metadata
                                if metadata.search_entry_point:
                                    st.caption("信息搜索方向:")
                                    # 解析 rendered_content 提取链接
                                    html_content = metadata.search_entry_point.rendered_content
                                    # print(f"DEBUG HTML CONTENT: {html_content}") # Debug
                                    
                                    # Try to find all links
                                    links = re.findall(r'<a\s+(?:[^>]*?\s+)?href="([^"]*)"[^>]*>(.*?)</a>', html_content, re.IGNORECASE | re.DOTALL)
                                    
                                    if links:
                                        for link, title in links:
                                            # Clean up title (remove tags if any)
                                            title = re.sub(r'<[^>]+>', '', title).strip()
                                            st.markdown(f"- [{title}]({link})")
                                    else:
                                        st.markdown(html_content, unsafe_allow_html=True)
                        else:
                            st.warning(f"未能获取 {asset} 的有效内容。")
                
                status_container.update(label="✅ 所有情报搜集完成！", state="complete", expanded=False)

            except Exception as e:
                st.error(f"全局错误: {e}")

# --- 5. 底部页脚 ---
st.markdown("---")
st.caption("💡 提示：输入标的越多，等待时间越长。建议一次查询 3-5 个标的。")