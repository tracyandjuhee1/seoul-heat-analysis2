# --- 모듈 4: 취약 계층 & 환경 분석 (연령대 세분화 적용) ---
st.subheader("👥 모듈 4: 취약 계층 및 발생 장소 타겟팅 분석")
col_pie1, col_pie2 = st.columns(2)

with col_pie1:
    if '나이' in filtered_df.columns:
        # 연령대를 10대 단위로 세분화하는 함수
        def categorize_age(age):
            if pd.isna(age):
                return '기타'
            age_int = int(age)
            if age_int < 20:
                return '10대 이하'
            elif age_int < 30:
                return '20대'
            elif age_int < 40:
                return '30대'
            elif age_int < 50:
                return '40대'
            elif age_int < 60:
                return '50대'
            elif age_int < 70:
                return '60대'
            else:
                return '70대 이상'

        filtered_df['연령대_세분화'] = filtered_df['나이'].apply(categorize_age)
        
        # 연령대별 바 차트 (또는 세분화된 파이 차트)로 표현하여 가독성 극대화
        age_agg = filtered_df.groupby('연령대_세분화')['출동건수'].sum().reset_index()
        # 정렬 순서 지정
        age_order = ['10대 이하', '20대', '30대', '40대', '50대', '60대', '70대 이상']
        
        fig_age = px.bar(age_agg, x='연령대_세분화', y='출동건수', title='연령대별 온열질환 발생 비중 (세분화)',
                         labels={'연령대_세분화': '연령대', '출동건수': '발생 건수'},
                         category_orders={'연령대_세분화': age_order},
                         color='출동건수', color_continuous_scale='Reds')
        st.plotly_chart(fig_age, use_container_width=True)

with col_pie2:
    if '발생장소' in filtered_df.columns:
        fig_loc = px.pie(filtered_df, names='발생장소', title='주요 발생 장소별 비중', hole=0.4,
                         color_discrete_sequence=px.colors.sequential.Sunset)
        st.plotly_chart(fig_loc, use_container_width=True)