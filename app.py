import streamlit as st
from google import genai

# ==========================================
# 🔑 1. 구글 Gemini AI 설정 
# ==========================================
API_KEY = st.secrets["GEMINI_API_KEY"]

if API_KEY and "여기에" not in API_KEY:
    client = genai.Client(api_key=API_KEY)
else:
    client = None

# ==========================================
# 🎨 2. 페이지 기본 설정 및 CSS
# ==========================================
st.set_page_config(page_title="이용약관 분석기", layout="wide")

st.markdown("""
<style>
    div[data-testid="column"]:nth-of-type(n) div.stButton > button:first-child {
        border-radius: 50px;
        height: 60px;
        width: 100%;
        font-weight: bold;
        border: 2px solid #4CAF50;
    }
    .stCheckbox label {
        font-size: 1.1rem;
    }
    .slide-arrow div.stButton > button:first-child {
        border-radius: 50%;
        height: 50px;
        width: 50px;
        font-size: 20px;
        border: 2px solid #ddd;
        background-color: #f9f9f9;
        color: #333;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 💾 3. 상태 관리 (Session State)
# ==========================================
if 'page' not in st.session_state: st.session_state['page'] = 0
if 'importance_scores' not in st.session_state:
    st.session_state['importance_scores'] = {'phone': 5, 'email': 5, 'dob': 5, 'location': 5}
if 'selected_keywords' not in st.session_state: st.session_state['selected_keywords'] = []
if 'chk_all' not in st.session_state: st.session_state['chk_all'] = False
if 'chk_req' not in st.session_state: st.session_state['chk_req'] = False
if 'tos_text' not in st.session_state: st.session_state['tos_text'] = ""
if 'subpage' not in st.session_state: st.session_state['subpage'] = 1
if 'analyzed' not in st.session_state: st.session_state['analyzed'] = False
if 'ai_parts' not in st.session_state: st.session_state['ai_parts'] = []

def sync_agreements(changed_key):
    st.session_state['chk_all'] = st.session_state[changed_key]
    st.session_state['chk_req'] = st.session_state[changed_key]

# ==========================================
# 🖥️ 4. 화면 렌더링
# ==========================================
if st.session_state['page'] == 0:
    st.title("🏠 서비스 메인 홈페이지")
    if st.button("앱 시작"): st.session_state['page'] = 1; st.rerun()
    st.stop()

elif st.session_state['page'] == 1:
    st.title("1단계: 사용자 개인정보 중요도 설정")
    st.write("### 아래 항목별 중요도를 0~10 사이로 설정해 주세요.")
    scores = st.session_state['importance_scores']
    st.session_state['importance_scores']['phone'] = st.slider("전화번호", 0, 10, scores['phone'])
    st.session_state['importance_scores']['email'] = st.slider("이메일", 0, 10, scores['email'])
    st.session_state['importance_scores']['dob'] = st.slider("출생년월일", 0, 10, scores['dob'])
    st.session_state['importance_scores']['location'] = st.slider("현재 위치", 0, 10, scores['location'])

elif st.session_state['page'] == 2:
    st.title("2단계: 중요 키워드 우선순위 선택")
    st.write("### 💭 중요하다고 생각하는 키워드를 순서대로 클릭해 주세요! (다시 누르면 취소됩니다)")
    
    available_keywords = [
        "위치 정보 무단 수집", "개인정보 제3자 제공", 
        "마케팅/광고 활용 동의", "데이터 해외 이전", 
        "민감 정보(건강/생체) 수집", "자동 연장 및 자동 결제", 
        "광고성 푸시 알림", "회원 탈퇴 후 정보 보관", 
        "타 앱 이용기록 수집", "작성 콘텐츠 저작권 귀속",
        "기기 정보 및 로그 수집", "음성/카메라 데이터 접근" 
    ]
    
    cols = st.columns(2)
    for i, kw in enumerate(available_keywords):
        with cols[i % 2]:
            is_selected = kw in st.session_state['selected_keywords']
            btn_type = "primary" if is_selected else "secondary"
            
            if st.button(kw, key=f"btn_{kw}", use_container_width=True, type=btn_type):
                if is_selected:
                    st.session_state['selected_keywords'].remove(kw)
                else:
                    st.session_state['selected_keywords'].append(kw)
                st.rerun()
                
    st.write("")
    st.info(f"**현재 선택된 키워드 ({len(st.session_state['selected_keywords'])}개):** " + 
            (", ".join(st.session_state['selected_keywords']) if st.session_state['selected_keywords'] else "없음"))

elif st.session_state['page'] == 3:
    st.title("3단계: 서비스 이용 약관 동의")
    with st.container(border=True):
        st.checkbox("✅ 모두 동의합니다.", key='chk_all', on_change=sync_agreements, args=('chk_all',))
        st.checkbox("(필수) 해당 앱에서 작성한 정보들에 대한 앱 내 사용에 동의합니다.", key='chk_req', on_change=sync_agreements, args=('chk_req',))

elif st.session_state['page'] == 4:
    st.title("4단계: 분석할 이용약관 입력")
    st.session_state['tos_text'] = st.text_area("이용약관을 복사&붙여넣기 해주세요.", value=st.session_state['tos_text'], height=300)
    st.session_state['analyzed'] = False 

elif st.session_state['page'] == 5:
    st.markdown("<h1 style='text-align: center; color: #1E88E5;'>📊 결 과</h1>", unsafe_allow_html=True)
    st.write("")

    if client is None:
        st.error("🚨 API 키가 설정되지 않았습니다! 코드 맨 위의 API_KEY 변수에 키를 넣어주세요.")
        st.stop()

    if not st.session_state['analyzed']:
        with st.spinner('🤖 실제 구글 Gemini AI 모델이 약관을 분석 중입니다... 잠시만 기다려주세요 (약 5~10초 소요)'):
            try:
                user_scores = st.session_state['importance_scores']
                user_keywords = ", ".join(st.session_state['selected_keywords']) if st.session_state['selected_keywords'] else "없음"
                tos_text = st.session_state['tos_text']

                # [수정됨] 0~100점 제한 및 5단계 세밀한 색상(HTML) 규칙 추가
                prompt = f"""
                너는 10년 차 개인정보 보호 전문 변호사야. 다음 [이용약관]을 분석해 줘.
                사용자는 중요도 설정에서 {user_scores} 만큼 비중을 두었고, 특히 중요 키워드로 [{user_keywords}]를 선택했어.

                [이용약관]
                {tos_text}

                ---
                답변은 반드시 아래 양식을 정확히 지켜서 작성해 줘. 구분선(---)을 기준으로 정확히 세 파트로 나누어 줘.

                [파트 1 영역]
                ### 🚨 개인정보 침해 우려 핵심 조항 요약
                (여기에 사용자가 설정한 가중치와 키워드를 바탕으로 가장 위험한 조항들을 요약해서 작성해 줘.)

                ---

                [파트 2 영역]
                ### 🔍 모든 약관 조항 분석 리포트
                (입력된 이용약관의 '모든 주요 조항'을 빠짐없이 분석하고 정리해 줘.)
                (아래의 [중요 규칙]에 따라 각각의 조항에 위험도 점수 태그를 반드시 표기할 것)

                ---

                [파트 3 영역]
                ### 🔥 위험도 TOP 10 세부 약관
                (분석한 조항들 중 위험도가 높은 순서대로 1위부터 10위까지만 추려서 나열해 줘.)
                (여기서도 아래의 [중요 규칙]에 따라 위험도 점수 태그를 반드시 표기할 것)
                
                **[중요 규칙]** 위험도 점수는 반드시 0점부터 100점 사이의 숫자로만 평가해. 또한, 파트 2와 파트 3에서 위험도 점수를 표시할 때는 무조건 점수 구간에 맞춰 아래의 HTML 코드를 복사해서 점수 숫자만 바꿔서 써!
                - 0점 ~ 20점: <span style='color: #8BC34A; font-weight: bold;'>[위험도 00점]</span>
                - 21점 ~ 40점: <span style='color: #FFC107; font-weight: bold;'>[위험도 00점]</span>
                - 41점 ~ 60점: <span style='color: #FF9800; font-weight: bold;'>[위험도 00점]</span>
                - 61점 ~ 80점: <span style='color: #F44336; font-weight: bold;'>[위험도 00점]</span>
                - 81점 ~ 100점: <span style='color: #000000; font-weight: bold; background-color: #FFCDD2; padding: 2px 4px; border-radius: 4px;'>[위험도 00점]</span>
                """

                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt
                )
                full_result = response.text

                if "---" in full_result:
                    parts = [part.strip() for part in full_result.split("---") if part.strip()]
                    st.session_state['ai_parts'] = parts
                else:
                    st.session_state['ai_parts'] = [full_result]

                st.session_state['analyzed'] = True
                st.session_state['subpage'] = 1 
                st.rerun()

            except Exception as e:
                st.error(f"AI 분석 중 에러가 발생했습니다: {e}")
                st.stop()

    max_subpages = len(st.session_state['ai_parts'])
    if max_subpages == 0: max_subpages = 1

    col_l, col_content, col_r = st.columns([1, 8, 1])
    with col_l:
        st.write(""); st.write(""); st.write("")
        st.markdown('<div class="slide-arrow">', unsafe_allow_html=True)
        if st.button("◀", key="prev_sub") and st.session_state['subpage'] > 1:
            st.session_state['subpage'] -= 1; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
            
    with col_r:
        st.write(""); st.write(""); st.write("")
        st.markdown('<div class="slide-arrow">', unsafe_allow_html=True)
        if st.button("▶", key="next_sub") and st.session_state['subpage'] < max_subpages:
            st.session_state['subpage'] += 1; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with col_content:
        st.write(f"### {st.session_state['subpage']}페이지 / 총 {max_subpages}페이지")
        idx = st.session_state['subpage'] - 1
        
        if idx < len(st.session_state['ai_parts']):
            with st.container(border=True): 
                # [수정됨] AI가 생성한 HTML(색상 태그)이 정상적으로 보이도록 unsafe_allow_html 옵션 추가
                st.markdown(st.session_state['ai_parts'][idx], unsafe_allow_html=True)

elif st.session_state['page'] == 6:
    st.title("6단계: 분석 완료 및 리포트 제공")
    st.success("🎉 성공적으로 모든 이용약관 분석 과정이 끝났습니다!")
    if st.button("처음부터 다시 하기"):
        st.session_state.clear(); st.rerun()

st.write(""); st.write("")
st.markdown("---")
col_back, col_space, col_next = st.columns([2, 6, 2])

with col_back:
    if st.session_state['page'] == 1:
        if st.button("⬅️ 이전 페이지로", use_container_width=True): st.session_state['page'] = 0; st.rerun()
    else:
        if st.button("⬅️ 뒤로가기", use_container_width=True):
            if st.session_state['page'] == 5: st.session_state['subpage'] = 1
            st.session_state['page'] -= 1; st.rerun()
with col_space: pass 
with col_next:
    if st.session_state['page'] == 1:
        if st.button("확인 ➡️", use_container_width=True, key="n1"): st.session_state['page']+=1; st.rerun()
    elif st.session_state['page'] == 2:
        if st.button("확인 ➡️", use_container_width=True, key="n2"): st.session_state['page']+=1; st.rerun()
    elif st.session_state['page'] == 3:
        if st.button("확인 ➡️", use_container_width=True, disabled=not st.session_state['chk_all'], key="n3"): st.session_state['page']+=1; st.rerun()
    elif st.session_state['page'] == 4:
        has_text = bool(st.session_state['tos_text'].strip())
        if st.button("확인 ➡️ (AI 분석)", use_container_width=True, disabled=not has_text, key="n4"): st.session_state['page']+=1; st.rerun()
    elif st.session_state['page'] == 5:
        if st.button("확인 ➡️ (완료)", use_container_width=True, type="primary", key="n5"): st.session_state['page']+=1; st.rerun()
