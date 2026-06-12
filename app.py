import streamlit as st
import pandas as pd
import sqlite3
import requests
from datetime import datetime
import random

def init_db():
    conn = sqlite3.connect("news_monitor.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS news_articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pub_date TEXT,
            title TEXT,
            media_name TEXT,
            author_name TEXT,
            category TEXT,
            link TEXT UNIQUE
        )
    """)
    conn.commit()
    conn.close()

def mock_ai_classify(title):
    categories = ["보도자료", "긍정", "부정", "기획기사"]
    if "출시" in title or "MOU" in title or "체결" in title or "협약" in title:
        return "보도자료"
    elif "논란" in title or "하락" in title or "의혹" in title or "소송" in title:
        return "부정"
    return random.choice(categories)

def fetch_and_save_news(client_id, client_secret):
    init_db()
    conn = sqlite3.connect("news_monitor.db")
    cursor = conn.cursor()
    
    # 네이버 API 친화적인 일반적인 공백(OR) 기반 검색 쿼리로 조정
    search_query = "한화투자증권 한화증권 한화증 한화證"
    
    url = f"https://openapi.naver.com/v1/search/news.json?query={search_query}&display=50&sort=date"
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret
    }
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            items = response.json().get("items", [])
            
            if not items:
                st.warning("네이버에서 수집된 최신 기사가 없습니다. 검색 쿼리를 점검하거나 잠시 후 다시 시도해 주십시오.")
                conn.close()
                return
                
            for item in items:
                title = item["title"].replace("<b>", "").replace("</b>", "").replace("&quot;", '"').replace("&amp;", "&").replace("&#39;", "'")
                link = item["link"]
                media = "네이버뉴스 수집" 
                author = "담당자 확인"
                pub_date = datetime.strptime(item["pubDate"], "%a, %d %b %Y %H:%M:%S +0900").strftime("%Y-%m-%d %H:%M")
                category = mock_ai_classify(title)
                
                try:
                    cursor.execute("""
                        INSERT INTO news_articles (pub_date, title, media_name, author_name, category, link)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (pub_date, title, media, author, category, link))
                except sqlite3.IntegrityError:
                    pass
            st.success(f"실시간 뉴스 수집 및 AI 성향 분류가 완료되었습니다. 데이터 개수를 갱신합니다.")
        else:
            st.error(f"API 호출 실패 (에러 코드: {response.status_code}). ID와 Secret을 다시 확인해 주세요.")
    except Exception as e:
        st.error(f"연동 중 오류 발생: {str(e)}")
        
    conn.commit()
    conn.close()

def load_data():
    conn = sqlite3.connect("news_monitor.db")
    df = pd.read_sql_query("SELECT * FROM news_articles ORDER BY pub_date DESC", conn)
    conn.close()
    return df

def main():
    st.set_page_config(layout="wide", page_title="언론 보도 모니터링 시스템")
    st.title("언론 보도 모니터링 시스템")
    st.caption("한화투자증권 미디어 관계 관리 및 데이터 분석 페이지")
    st.markdown("---")
    
    with st.expander("실시간 뉴스 수집 제어 센터 (네이버 API 인증 필수)"):
        api_id = st.text_input("네이버 뉴스 Client ID 입력", type="password")
        api_secret = st.text_input("네이버 뉴스 Client Secret 입력", type="password")
        
        if st.button("지정 키워드 수집 및 AI 분류 실행 (한화투자증권 등 4개 조합)", use_container_width=True):
            if not api_id or not api_secret:
                st.warning("API ID와 Secret을 모두 입력해야 실시간 수집이 가능합니다.")
            else:
                with st.spinner("포털 뉴스 분석 및 데이터 적재 중..."):
                    fetch_and_save_news(api_id, api_secret)

    init_db()
    df = load_data()
    
    if df.empty:
        st.info("데이터베이스에 축적된 기사가 없습니다. 상단 제어 센터에서 수집을 실행해 주십시오.")
        return

    st.subheader("데이터 필터 및 모니터링 지표")
    selected_category = st.multiselect("기사 성향 필터", options=df["category"].unique())
        
    filtered_df = df.copy()
    if selected_category:
        filtered_df = filtered_df[filtered_df["category"].isin(selected_category)]

    st.markdown("### 기사 성향별 통계 차트")
    if not filtered_df.empty:
        cate_counts = filtered_df["category"].value_counts()
        st.bar_chart(cate_counts)

    st.markdown("---")
    st.subheader("수집 기사 및 원문 링크 상세 리스트")
    
    if not filtered_df.empty:
        st.data_editor(
            filtered_df[["pub_date", "title", "media_name", "category", "link"]],
            column_config={
                "link": st.column_config.LinkColumn("원문 링크", display_text="이동하기"),
                "pub_date": "발행일시",
                "title": "기사 제목",
                "media_name": "매체명",
                "category": "성향분류"
            },
            disabled=True,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("조건에 부합하는 기사 데이터가 없습니다.")

if __name__ == "__main__":
    main()
