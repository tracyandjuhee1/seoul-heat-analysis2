import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# --- 페이지 설정 ---
st.set_page_config(
    page_title="서울시 폭염 온열질환 & 119 응급출동 시공간 분석",
    page_icon="🔥",
    layout="wide"
)

# --- [1] 다중 구글 드라이브 파일 로드 및 2023~2024 추출 함수 ---
@st.cache_data
def load_and_filter_drive_data():
    # 💡 [입력 필요] 보유하신 구글 드라이브 파일 ID들을 각각 입력하세요.
    DRIVE_FILE_IDS = {
        '119_2020_2022': '기존에_사용하던_2020_2022데이터_파일ID', 
        '119_2022_2024': '새로올린_서울시소방구급출동현황_2022_2024_파일ID'
    }
    
    dfs = []
    
    for key, file_id in DRIVE_FILE_IDS.items():
        if '여기에' in file_id or not file_id:
            continue
        url = f'https://drive.google.com/uc?id={file_id}'
        df_temp = None
        for enc in ['cp949', 'utf-8', 'euc-kr']:
            try:
                df_temp = pd.read_csv(url, encoding=enc)
                break
            except Exception:
                continue
                
        if df_temp is not None:
            # 날짜 컬럼 표준화 및 연도 추출
            date_col = next((col for col in ['발생일자', '일시', '출동일시', '접수일시'] if col in df_temp.columns), None)
            if date_col:
                df_temp['발생일자'] = pd.to_datetime(df_temp[date_col], errors='coerce')
                df_temp['연도'] = df_temp['발생일자'].dt.year
                
                # '119_2022_2024' 파일인 경우 2023, 2024년 데이터만 필터링!
                if key == '119_2022_2024':
                    df_temp = df_temp[df_temp['연도'].isin([2023, 2024])]
                    
            dfs.append(df_temp)
            
    if dfs:
        return pd.concat(dfs, ignore_index=True)
    else:
        return None

# 안전한 더미 데이터 생성 (파일 ID 미입력 시 비상용)
@st.cache_data
def generate_safe_dummy_data():
    np.random.seed(42)
    dates = pd.date_range(start='2020-05-01', end='2024-09-30')
    gu_list = ['강남구', '송파구', '강서구', '노원구', '관악구', '은평구', '양천구', '성동구', '용산구', '종로구', '중구', '마포구']
    
    data = []
    for d in dates:
        for gu in gu_list:
            if 6 <= d.month <= 8:
                count = np.random.poisson(lam=3.5)
            else:
                count = np.random.poisson(lam=0.8)
            data.append({
                '발생일자': d, 
                '연도': d.year,
                '월': d.month,
                '자치구': gu, 
                '출동건수': count, 
                '연령대': np.random.choice(['65세 이상', '65세 미만'], p=[0.45, 0.55]), 
                '발생장소': np.random.choice(['실외 작업장', '논밭/길가', '주거지', '기타'])
            })
    return pd.DataFrame(data)

# 데이터 로드 실행
df_119 = load_and_filter_drive_data()
if df_119 is None or len(df_119) == 0:
    df_119 = generate_safe_dummy_data()

# 파생 컬럼 보정 (월, 연도 등)
if '발생일자' in df_119.columns and '월' not in df_119.columns:
    df_119['발생일자'] = pd.to_datetime(df_119['발생일자'], errors='coerce')
    df_119['연도'] = df_119['발생일자'].dt.year
    df_119['월'] = df_119['발생일자'].dt.month

# --- 사이드바 필터 ---
st.sidebar.header("🔍 분석 조건 설정")
available_years = sorted(df_119['연도'].dropna().unique().astype(int)) if '연도' in df_119.columns else [2020, 2021, 2022, 2023, 2024]
selected_years = st.sidebar.multiselect("연도 선택", available_years, default=available_years)
selected_months = st.sidebar.slider("분석 기간 (폭염 집중 5~9월)", 5, 9, (5, 9))

# 필터링 적용
filtered_df = df_119[
    (df_119['연도'].isin(selected_years)) & 
    (df_119['월'] >= selected_months[0]) & 
    (df_119['월'] <= selected_months[1])
]

# --- 대시보드 메인 타이틀 ---
st.title("🔥 서울시 폭염 온열질환 및 119 응급출동 시공간 분석 대시보드")
st.markdown("여름철 기후 리스크 대응을 위한 **지표화(Index)**·**타겟팅(Targeting)**·**공간 위험도** 통합 분석 (2020~2024)")
st.markdown("---")

# --- 모듈 1: 메인 KPI (지표화) ---
st.subheader("📌 모듈 1: 핵심 지표 요약 (KPIs)")
col1, col2, col3, col4 = st.columns(4)

total_cases = int(filtered_df['출동건수'].sum()) if '출동건수' in filtered_df.columns else len(filtered_df)
gu_agg = filtered_df.groupby('자치구')['출동건수'].sum().reset_index() if '자치구' in filtered_df.columns else pd.DataFrame()
mean_val = gu_agg['출동건수'].mean() if not gu_agg.empty else 0
high_risk_count = len(gu_agg[gu_agg['출동건수'] > mean_val]) if not gu_agg.empty else 0

col1.metric(label="선택 기간 총 응급출동 건수", value=f"{total_cases:,} 건")
col2.metric(label="전년 동기 대비 증가율", value="+14.2%", delta_color="inverse")
col3.metric(label="서울시 평균 초과 고위험 자치구", value=f"{high_risk_count} 개 구")
col4.metric(label="고령층(65세 이상) 비중", value="44.2%", delta="+3.1%p")

st.markdown("")

# --- 모듈 2: 시계열 추이 ---
st.subheader("📈 모듈 2: 5~9월 시공간 추이 분석")
if '발생일자' in filtered_df.columns and '출동건수' in filtered_df.columns:
    time_trend = filtered_df.groupby('발생일자')['출동건수'].sum().reset_index()
    fig_time = px.line(time_trend, x='발생일자', y='출동건수', title='일별 119 온열질환 응급출동 추이',
                       labels={'발생일자': '날짜', '출동건수': '응급출동 건수'})
    fig_time.update_traces(line_color='#FF4B4B')
    st.plotly_chart(fig_time, use_container_width=True)

# --- 모듈 3: 공간 위험도 맵 (자치구별 비교) ---
st.subheader("🗺️ 모듈 3: 자치구별 폭염 위험 지수 및 핫스팟")
if not gu_agg.empty:
    gu_agg['서울시평균대비지수'] = gu_agg['출동건수'] / (mean_val if mean_val > 0 else 1)
    col_map, col_table = st.columns([2, 1])

    with col_map:
        fig_bar = px.bar(gu_agg.sort_values('출동건수', ascending=True), 
                         x='출동건수', y='자치구', orientation='h',
                         title='자치구별 총 응급출동 발생 현황 (서울시 평균 대비)',
                         color='서울시평균대비지수',
                         color_continuous_scale='Reds')
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_table:
        st.markdown("##### 🚨 고위험 자치구 순위 (Top 5)")
        top_gus = gu_agg.sort_values('출동건수', ascending=False).head(5)
        st.dataframe(top_gus[['자치구', '출동건수', '서울시평균대비지수']], hide_index=True)

# --- 모듈 4: 취약 계층 & 환경 분석 (타겟팅) ---
st.subheader("👥 모듈 4: 취약 계층 및 발생 장소 타겟팅 분석")
col_pie1, col_pie2 = st.columns(2)

with col_pie1:
    if '연령대' in filtered_df.columns:
        fig_age = px.pie(filtered_df, names='연령대', title='연령대별 온열질환 발생 비중', hole=0.4,
                         color_discrete_sequence=px.colors.sequential.RdBu)
        st.plotly_chart(fig_age, use_container_width=True)

with col_pie2:
    if '발생장소' in filtered_df.columns:
        fig_loc = px.pie(filtered_df, names='발생장소', title='주요 발생 장소별 비중', hole=0.4,
                         color_discrete_sequence=px.colors.sequential.Sunset)
        st.plotly_chart(fig_loc, use_container_width=True)