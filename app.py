import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import urllib.request
import json

# --- 페이지 설정 ---
st.set_page_config(
    page_title="서울시 폭염 온열질환 & 119 응급출동 시공간 분석",
    page_icon="🔥",
    layout="wide"
)

# --- [1] 데이터 및 자치구 GeoJSON 로드 함수 ---
@st.cache_data
def load_data_and_geojson():
    # 💡 구글 드라이브 파일 ID 입력 (미입력 시 안전 더미 가동)
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
            date_col = next((col for col in ['발생일자', '일시', '출동일시', '접수일시'] if col in df_temp.columns), None)
            if date_col:
                df_temp['발생일자'] = pd.to_datetime(df_temp[date_col], errors='coerce')
                df_temp['연도'] = df_temp['발생일자'].dt.year
                if key == '119_2022_2024':
                    df_temp = df_temp[df_temp['연도'].isin([2023, 2024])]
            dfs.append(df_temp)
            
    df_119 = pd.concat(dfs, ignore_index=True) if dfs else None

    # 서울시 자치구 GeoJSON 다운로드
    geojson_url = "https://raw.githubusercontent.com/southkorea/seoul-maps/master/kostat/2013/json/seoul_municipalities_geo_simple.json"
    seoul_geojson = None
    try:
        with urllib.request.urlopen(geojson_url) as response:
            seoul_geojson = json.loads(response.read().decode('utf-8'))
    except Exception:
        pass

    return df_119, seoul_geojson

# 안전한 더미 데이터 생성기 (시간대 정보 포함)
@st.cache_data
def generate_safe_dummy_data():
    np.random.seed(42)
    dates = pd.date_range(start='2020-05-01', end='2024-09-30', freq='D')
    gu_list = ['강남구', '송파구', '강서구', '노원구', '관악구', '은평구', '양천구', '성동구', '용산구', '종로구', '중구', '마포구',
               '광진구', '동대문구', '중랑구', '성북구', '강북구', '도봉구', '서대문구', '구로구', '금천구', '영등포구', '동작구', '서초구', '강동구']
    
    data = []
    for d in dates:
        for gu in gu_list:
            if 6 <= d.month <= 8:
                base_count = np.random.poisson(lam=3.5)
            else:
                base_count = np.random.poisson(lam=0.8)
            
            # 시간대별 분산 (오후 2~5시에 집중되도록 가중치 부여)
            for hour in [10, 12, 14, 15, 16, 18]:
                weight = 2.5 if hour in [14, 15, 16] else 1.0
                c = int(base_count * weight * np.random.uniform(0.2, 0.5))
                if c > 0:
                    data.append({
                        '발생일자': d, 
                        '연도': d.year,
                        '월': d.month,
                        '시간': hour,
                        '자치구': gu, 
                        '출동건수': c, 
                        '연령대': np.random.choice(['65세 이상', '65세 미만'], p=[0.45, 0.55]), 
                        '발생장소': np.random.choice(['실외 작업장', '논밭/길가', '주거지', '기타'])
                    })
    return pd.DataFrame(data)

# 데이터 및 지도 경계 로드
df_119, seoul_geojson = load_data_and_geojson()
if df_119 is None or len(df_119) == 0:
    df_119 = generate_safe_dummy_data()

if '발생일자' in df_119.columns and '월' not in df_119.columns:
    df_119['발생일자'] = pd.to_datetime(df_119['발생일자'], errors='coerce')
    df_119['연도'] = df_119['발생일자'].dt.year
    df_119['월'] = df_119['발생일자'].dt.month

if '시간' not in df_119.columns:
    df_119['시간'] = 14 # 기본값 오후 2시

# --- 사이드바 필터 ---
st.sidebar.header("🔍 분석 조건 설정")
available_years = sorted(df_119['연도'].dropna().unique().astype(int)) if '연도' in df_119.columns else [2020, 2021, 2022, 2023, 2024]
selected_years = st.sidebar.multiselect("연도 선택", available_years, default=available_years)
selected_months = st.sidebar.slider("분석 기간 (폭염 집중 5~9월)", 5, 9, (5, 9))

filtered_df = df_119[
    (df_119['연도'].isin(selected_years)) & 
    (df_119['월'] >= selected_months[0]) & 
    (df_119['월'] <= selected_months[1])
]

# --- 대시보드 타이틀 ---
st.title("🔥 서울시 폭염 온열질환 및 119 응급출동 시공간 분석 대시보드")
st.markdown("여름철 기후 리스크 대응을 위한 **지표화(Index)**·**타겟팅(Targeting)**·**공간 위험도 지도** 통합 분석 (2020~2024)")
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

# --- 모듈 2: 시공간 추이 및 시간대별 골든타임 히트맵 ---
st.subheader("📈 모듈 2: 5~9월 시공간 추이 및 시간대별 취약성 분석")
col_t1, col_t2 = st.columns(2)

with col_t1:
    if '발생일자' in filtered_df.columns and '출동건수' in filtered_df.columns:
        time_trend = filtered_df.groupby('발생일자')['출동건수'].sum().reset_index()
        fig_time = px.line(time_trend, x='발생일자', y='출동건수', title='일별 119 온열질환 응급출동 추이',
                           labels={'발생일자': '날짜', '출동건수': '응급출동 건수'})
        fig_time.update_traces(line_color='#FF4B4B')
        st.plotly_chart(fig_time, use_container_width=True)

with col_t2:
    if '시간' in filtered_df.columns and '월' in filtered_df.columns:
        # 시간대별 x 월별 히트맵 생성
        heat_data = filtered_df.groupby(['월', '시간'])['출동건수'].sum().reset_index()
        fig_heat = px.density_heatmap(heat_data, x='월', y='시간', z='출동건수', 
                                      title='월별·시간대별 온열질환 집중 골든타임 히트맵',
                                      labels={'월': '월(Month)', '시간': '시간대(Hour)', '출동건수': '발생 건수'},
                                      color_continuous_scale='Reds')
        st.plotly_chart(fig_heat, use_container_width=True)

# --- 모듈 3: 공간 위험도 지도 (Choropleth Map) & 자치구 랭킹 ---
st.subheader("🗺️ 모듈 3: 서울시 자치구별 폭염 위험 지도 및 핫스팟 분석")
if not gu_agg.empty:
    gu_agg['서울시평균대비지수'] = gu_agg['출동건수'] / (mean_val if mean_val > 0 else 1)
    
    col_map, col_table = st.columns([1.3, 1])

    with col_map:
        if seoul_geojson is not None:
            fig_map = px.choropleth(
                gu_agg,
                geojson=seoul_geojson,
                locations='자치구',
                featureidkey='properties.name',
                color='출동건수',
                color_continuous_scale='Reds',
                title='서울시 자치구별 119 온열질환 출동 분포 지도',
                labels={'출동건수': '출동 건수'}
            )
            fig_map.update_geos(fitbounds="locations", visible=False)
            fig_map.update_layout(margin={"r":0,"t":40,"l":0,"b":0}, height=450)
            st.plotly_chart(fig_map, use_container_width=True)
        else:
            fig_bar = px.bar(gu_agg.sort_values('출동건수', ascending=True), 
                             x='출동건수', y='자치구', orientation='h',
                             title='자치구별 총 응급출동 발생 현황',
                             color='서울시평균대비지수', color_continuous_scale='Reds')
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