import streamlit as st
import re
import asyncio
from google import genai
from google.genai import types
import datetime
import pytz # 需要安装: pip install pytz

# --- 1. 页面基础配置 ---
st.set_page_config(page_title="Crypto 情报终端", page_icon="🚀", layout="wide")

st.title("🚀 Crypto 情报终端")
st.caption("由 Gemini 2.0 Flash & Google Search 提供支持 | 宏观/微观双模式")

# --- 2. 侧边栏配置 (全局设置) ---
with st.sidebar:
    st.header("⚙️ 全局设置")
    api_key = st.text_input("Gemini API Key", type="password", help="在此输入你的 Google AI Studio Key")    
    
    st.markdown("---")
    st.markdown("### 📅 时间范围")
    time_range = st.selectbox(
        "选择回溯时间",
        options=["过去 4 小时", "过去 24 小时", "过去 3 天", "过去 7 天"],
        index=1 
    )

# --- 3. 核心逻辑函数 ---

def get_current_beijing_time():
    """获取格式化的北京时间"""
    beijing_tz = pytz.timezone('Asia/Shanghai')
    now = datetime.datetime.now(beijing_tz)
    return now.strftime("%Y-%m-%d %H:%M")

def get_market_news_report(client, time_str):
    """
    新功能：全网新闻聚合 (Strict Mode)
    """
    current_time = get_current_beijing_time()
    
    # 核心：将之前调试好的 Prompt 注入
    # 注意：我们直接把当前时间喂给 AI，不需要它再写代码去算
    prompt = f"""
    Current Beijing Time (Anchor): **{current_time}**.
    Timeframe to search: **{time_str}**.

    ### Role & Objective
    You are an expert Cryptocurrency Market Intelligence Analyst. Your goal is to aggregate recent news strictly from the **Target Source List**.
    
    ### Target Source List (Iterate through EACH)
    1. CoinDesk, Cointelegraph, The Block, Decrypt
    2. Foresight News, BlockBeats, Odaily, PANews, Wu Blockchain, Jinse Finance
    3. CoinMarketCap, CoinGecko, RootData
    4. Bloomberg Crypto, CNBC Crypto

    ### Operational Workflow
    1. **Search:** Use Google Search to retrieve news for the requested timeframe ({time_str}) for the sources above.
    2. **Calc:** Convert all relative times (e.g., "3 hours ago") to absolute **Beijing Time** based on the Anchor Time: {current_time}.
    3. **Filter:** Focus on major events only.

    ### Strict Output Format
    Output in **Chinese**. You must output a separate section for EVERY website group or major website.

    **Format Structure:**
    ### [Website Name]
    *   **[MM-DD HH:mm] [News Title]**: Summary of the event.
    *   *(If no news is found, state: "该时段内无重大独立报道")*

    ... (Repeat for sources) ...

    ### Overall Sentiment Summary
    *   A brief paragraph on market sentiment (Bullish/Bearish/Neutral) and main drivers.
    """

    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash', # 建议使用最新的 Flash 模型
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                response_modalities=["TEXT"]
            )
        )
        return response
    except Exception as e:
        return f"Error: {str(e)}"

def get_asset_report(client, asset, time_str):
    """
    原功能：单个标的分析
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
       - **数量限制**：最多输出 15 条。
       - 每条格式：【时间/来源】+ 新闻内容 + (对价格的影响分析)。
    """

    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                response_modalities=["TEXT"]
            )
        )
        return response
    except Exception as e:
        return f"Error: {str(e)}"

# 辅助函数：解析 Google Grounding 的链接
def display_grounding_links(response):
    if hasattr(response, 'candidates') and response.candidates:
        candidate = response.candidates[0]
        if hasattr(candidate, 'grounding_metadata') and candidate.grounding_metadata:
            metadata = candidate.grounding_metadata
            if metadata.search_entry_point:
                with st.expander("🔗 查看原始引用来源", expanded=False):
                    st.markdown(metadata.search_entry_point.rendered_content, unsafe_allow_html=True)

async def get_asset_report_async(client, asset, time_str):
    return await asyncio.to_thread(get_asset_report, client, asset, time_str)

async def get_market_news_async(client, time_str):
    return await asyncio.to_thread(get_market_news_report, client, time_str)

# --- 4. 主界面交互 (Tab 结构) ---

if not api_key:
    st.warning("👈 请先在左侧侧边栏输入 Gemini API Key 以开始使用。")
else:
    client = genai.Client(api_key=api_key)
    
    # 创建两个选项卡
    tab1, tab2 = st.tabs(["📰 全球市场速览 (News)", "🪙 币种深度投研 (Assets)"])

    # === Tab 1: 全球市场速览 (新功能) ===
    with tab1:
        st.subheader("全网主流媒体信息聚合")
        st.info(f"当前模式：扫描 **{time_range}** 内全球 15+ 顶流 Crypto 媒体的突发新闻。")
        
        if st.button("🚀 扫描全网新闻", type="primary", key="btn_market"):
            with st.spinner("正在同步北京时间并检索全球媒体数据..."):
                # 异步调用新函数
                result = asyncio.run(get_market_news_async(client, time_range))
                
                if isinstance(result, str) and "Error" in result:
                    st.error(result)
                elif hasattr(result, 'text'):
                    st.markdown(result.text)
                    display_grounding_links(result)
                else:
                    st.error("未能获取数据，请重试。")

    # === Tab 2: 币种深度投研 (原功能) ===
    with tab2:
        st.subheader("指定标的信息收集")
        
        # 将原来的输入框移到这里
        assets_input = st.text_input(
            "输入代币名称 (用逗号分隔)", 
            value="BTC, ETH, SOL",
            placeholder="例如: BTC, PEPE, WIF",
            key="asset_input"
        )
        
        if st.button("🔍 开始分析标的", key="btn_assets"):
            assets_list = [x.strip().upper() for x in assets_input.split(',') if x.strip()]

            if not assets_list:
                st.warning("请输入至少一个标的。")
            else:
                try:
                    status_container = st.status("正在启动 AI 研究员...", expanded=True)
                    
                    async def run_analysis():
                        tasks = []
                        for asset in assets_list:
                            status_container.write(f"🕵️ 正在搜集 {asset} 的情报...")
                            tasks.append(get_asset_report_async(client, asset, time_range))
                        return await asyncio.gather(*tasks)

                    results = asyncio.run(run_analysis())
                    
                    for i, asset in enumerate(assets_list):
                        response = results[i]
                        with st.expander(f"📊 {asset} 分析报告", expanded=True):
                            if isinstance(response, str) and "Error" in response:
                                st.error(f"搜索 {asset} 时发生错误: {response}")
                            elif hasattr(response, 'text'):
                                st.markdown(response.text)
                                display_grounding_links(response)
                            else:
                                st.warning(f"未能获取 {asset} 的有效内容。")
                    
                    status_container.update(label="✅ 所有情报搜集完成！", state="complete", expanded=False)

                except Exception as e:
                    st.error(f"运行时错误: {e}")

# --- 5. 底部页脚 ---
st.markdown("---")
st.caption("提示：'全球市场速览' 消耗 Tokens 较多，建议使用 Gemini 1.5 Pro 或 2.0 Flash 模型。")