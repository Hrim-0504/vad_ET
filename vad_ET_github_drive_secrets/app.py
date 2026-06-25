import csv
import random
import re
from datetime import datetime
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components


# =========================
# 기본 설정
# =========================
st.set_page_config(
    page_title="VAD 영상 정서 평가 실험",
    page_icon="🎥",
    layout="centered",
)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
RESPONSE_CSV = DATA_DIR / "responses.csv"

VIDEO_ID_RE = re.compile(r"(?:/d/|id=)([A-Za-z0-9_-]+)")


# =========================
# 스타일
# =========================
st.markdown(
    """
    <style>
    .block-container {
        max-width: 980px;
        padding-top: 2.5rem;
        padding-bottom: 4rem;
    }
    .main-card {
        background: #ffffff;
        border: 1px solid #d1d5db;
        border-radius: 22px;
        padding: 36px 34px;
        box-shadow: 0 10px 28px rgba(15, 23, 42, 0.08);
        margin-bottom: 24px;
    }
    .center-title {
        text-align: center;
        font-size: 30px;
        font-weight: 900;
        color: #111827;
        margin-bottom: 22px;
    }
    .body-text {
        font-size: 18px;
        line-height: 2;
        color: #374151;
        word-break: keep-all;
    }
    .section-box {
        margin-top: 22px;
        padding: 20px 22px;
        border-radius: 16px;
        background: #f9fafb;
        border: 1px solid #e5e7eb;
        font-size: 17px;
        line-height: 1.8;
        word-break: keep-all;
    }
    .section-title {
        font-size: 19px;
        font-weight: 800;
        color: #111827;
        margin-bottom: 8px;
    }
    .blue-pill {
        display: inline-block;
        margin-bottom: 22px;
        padding: 8px 18px;
        border-radius: 999px;
        background: #eff6ff;
        border: 1px solid #bfdbfe;
        color: #2563eb;
        font-size: 17px;
        font-weight: 800;
    }
    .warning-card {
        background: #fef3c7;
        border: 2px solid #f59e0b;
        border-radius: 22px;
        padding: 38px 34px;
        text-align: center;
        box-shadow: 0 10px 28px rgba(15, 23, 42, 0.08);
    }
    .warning-red {
        color: #dc2626;
        font-size: 21px;
        font-weight: 900;
        line-height: 1.8;
        margin-top: 22px;
        word-break: keep-all;
    }
    .video-frame {
        border: 1px solid #d1d5db;
        border-radius: 16px;
        overflow: hidden;
        background: #000000;
        margin-top: 18px;
        margin-bottom: 18px;
    }
    .vad-card {
        margin-bottom: 30px;
        padding: 24px;
        border: 1px solid #e5e7eb;
        border-radius: 16px;
        background: #ffffff;
    }
    .vad-title {
        font-size: 1.15rem;
        font-weight: 800;
        margin-bottom: 8px;
        color: #111827;
    }
    .vad-desc {
        color: #4b5563;
        line-height: 1.8;
        margin-bottom: 16px;
        font-size: 15px;
        word-break: keep-all;
    }
    .small-muted {
        color: #6b7280;
        font-size: 14px;
        line-height: 1.7;
        word-break: keep-all;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================
# 유틸 함수
# =========================
def extract_drive_file_id(value: str) -> str:
    """Google Drive 공유 링크 또는 파일 ID에서 file_id만 추출."""
    value = str(value).strip()
    match = VIDEO_ID_RE.search(value)
    if match:
        return match.group(1)
    return value


def natural_key(text: str):
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", text)]


@st.cache_data(show_spinner=False)
def get_video_items_from_secrets():
    """Streamlit Secrets의 [videos] 섹션에서 영상 목록 읽기."""
    try:
        videos_raw = dict(st.secrets["videos"])
    except Exception:
        return []

    items = []
    for key, raw_value in videos_raw.items():
        file_id = extract_drive_file_id(raw_value)
        if file_id and "PASTE_GOOGLE" not in file_id:
            items.append({"key": str(key), "file_id": file_id})

    items.sort(key=lambda x: natural_key(x["key"]))
    return items


def get_app_setting(name: str, default):
    try:
        return st.secrets.get("app", {}).get(name, default)
    except Exception:
        return default


def get_sets_per_block() -> int:
    try:
        return int(get_app_setting("sets_per_block", 25))
    except Exception:
        return 25


def get_randomize_videos() -> bool:
    value = get_app_setting("randomize_videos", True)
    if isinstance(value, bool):
        return value
    return str(value).lower() in ["true", "1", "yes", "y"]


def make_drive_preview_url(file_id: str) -> str:
    return f"https://drive.google.com/file/d/{file_id}/preview"


def current_block_number(round_index_zero_based: int) -> int:
    return (round_index_zero_based // get_sets_per_block()) + 1


def save_response(row: dict):
    fieldnames = [
        "timestamp",
        "participant_id",
        "round_number",
        "block_number",
        "video_key",
        "drive_file_id",
        "vad_valence",
        "vad_arousal",
        "vad_dominance",
    ]
    file_exists = RESPONSE_CSV.exists()
    with RESPONSE_CSV.open("a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def go_to(page_name: str):
    st.session_state.page = page_name
    st.rerun()


def init_experiment(participant_id: str, video_items: list):
    order = list(range(len(video_items)))
    if get_randomize_videos():
        random.shuffle(order)

    st.session_state.started = True
    st.session_state.participant_id = participant_id
    st.session_state.video_order = order
    st.session_state.round_index = 0
    st.session_state.page = "experiment_info"


def current_video(video_items: list):
    idx = st.session_state.video_order[st.session_state.round_index]
    return video_items[idx]


# =========================
# 페이지 함수
# =========================
def page_missing_secrets():
    st.markdown('<div class="main-card">', unsafe_allow_html=True)
    st.markdown('<div class="center-title">Google Drive 영상 목록이 필요합니다</div>', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="body-text">
        아직 Streamlit Secrets에 영상 파일 ID가 들어가지 않았습니다.<br>
        로컬에서는 <code>.streamlit/secrets.toml</code> 파일을 만들고,<br>
        Streamlit Cloud에서는 App settings → Secrets에 아래 형식으로 넣어주세요.
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.code(
        """[app]
sets_per_block = 25
randomize_videos = true

[videos]
video_001 = "Google Drive 파일 ID 또는 공유 링크"
video_002 = "Google Drive 파일 ID 또는 공유 링크"
video_003 = "Google Drive 파일 ID 또는 공유 링크""",
        language="toml",
    )
    st.markdown("</div>", unsafe_allow_html=True)


def page_participant_start(video_items: list):
    st.markdown('<div class="main-card">', unsafe_allow_html=True)
    st.markdown('<div class="center-title">VAD 영상 정서 평가 실험</div>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="body-text">
        총 영상 수: <b>{len(video_items)}</b>개<br>
        각 영상 시청 후 쾌락, 각성, 통제 차원을 1점부터 9점까지 평가합니다.
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    with st.form("participant_form"):
        participant_id = st.text_input("참가자 ID를 입력하세요", placeholder="예: P001")
        submitted = st.form_submit_button("실험 시작")

    if submitted:
        if not participant_id.strip():
            st.error("참가자 ID를 입력해 주세요.")
        else:
            init_experiment(participant_id.strip(), video_items)
            st.rerun()


def page_experiment_info():
    st.markdown('<div class="main-card">', unsafe_allow_html=True)
    st.markdown('<div class="center-title">실험 설명</div>', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="body-text">
        본 실험은 영상을 시청한 뒤, 영상에서 느껴지는 정서를 평가하는 방식으로 진행됩니다.
        </div>

        <div class="section-box">
            <div class="section-title">1. 실험 진행 순서</div>
            각 세트는 <b>영상 시청 → 정서 평가 설문</b> 순서로 진행됩니다.
        </div>

        <div class="section-box">
            <div class="section-title">2. 영상 시청 안내</div>
            화면에 제시되는 Google Drive 영상을 끝까지 시청해 주세요.
        </div>

        <div class="section-box">
            <div class="section-title">3. 설문 응답 안내</div>
            설문에서는 각 문항에 대해 가장 적절하다고 느끼는 값을 선택해 주세요.<br>
            정답은 없으므로, 영상에서 느낀 감정에 따라 응답해 주시면 됩니다.
        </div>

        <div class="section-box">
            <div class="section-title">4. 블록 및 쉬는 시간 안내</div>
            실험은 일정한 영상 수 단위로 블록이 나뉘며, 블록 사이에 쉬는 시간이 제공됩니다.
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    if st.button("다음", type="primary"):
        go_to("block_start")


def page_block_start():
    block_number = current_block_number(st.session_state.round_index)
    st.markdown(
        f"""
        <div class="main-card" style="text-align:center;">
            <div class="blue-pill">{block_number}번째 블록</div>
            <div class="center-title">이제 실험을 시작하겠습니다.</div>
            <div class="body-text">
                준비가 되셨다면<br>
                다음 버튼을 눌러주세요.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("다음", type="primary"):
        go_to("video")


def page_video(video_items: list):
    round_number = st.session_state.round_index + 1
    total_rounds = len(video_items)
    video = current_video(video_items)
    preview_url = make_drive_preview_url(video["file_id"])

    st.markdown(
        f"""
        <div class="main-card">
            <div class="center-title">영상 {round_number} / {total_rounds}</div>
            <div class="body-text" style="text-align:center;">
                아래 영상을 끝까지 시청해 주세요.<br>
                영상 시청이 끝난 뒤 버튼을 눌러 설문으로 이동합니다.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    iframe_html = f"""
    <div class="video-frame">
        <iframe
            src="{preview_url}"
            width="100%"
            height="500"
            allow="autoplay; fullscreen"
            allowfullscreen
            style="border:0; display:block;">
        </iframe>
    </div>
    """
    components.html(iframe_html, height=530)

    st.markdown(
        '<div class="small-muted">Google Drive 권한이 제한되어 있으면, 참가자가 공유받은 Google 계정으로 로그인해야 영상이 보입니다.</div>',
        unsafe_allow_html=True,
    )

    if st.button("영상을 끝까지 봤습니다", type="primary"):
        go_to("survey")


def image_if_exists(path: Path, caption: str):
    if path.exists():
        st.image(str(path), caption=caption, use_container_width=True)
    else:
        st.info(f"이미지 파일이 없습니다: {path.name}")


def vad_question(title: str, desc: str, image_name: str, left_label: str, right_label: str, key: str):
    st.markdown('<div class="vad-card">', unsafe_allow_html=True)
    st.markdown(f'<div class="vad-title">{title}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="vad-desc">{desc}</div>', unsafe_allow_html=True)
    image_if_exists(BASE_DIR / "assets" / image_name, caption="")
    st.markdown(
        f"<div class='small-muted'><b>1</b> = {left_label} &nbsp;&nbsp;&nbsp; <b>9</b> = {right_label}</div>",
        unsafe_allow_html=True,
    )
    value = st.radio(
        "값을 선택하세요",
        options=list(range(1, 10)),
        index=None,
        horizontal=True,
        key=key,
        label_visibility="collapsed",
    )
    st.markdown("</div>", unsafe_allow_html=True)
    return value


def page_survey(video_items: list):
    round_number = st.session_state.round_index + 1
    total_rounds = len(video_items)
    video = current_video(video_items)

    st.markdown(
        f"""
        <div class="main-card">
            <div class="center-title">정서 평가 설문</div>
            <div class="body-text" style="text-align:center;">
                영상 {round_number} / {total_rounds}<br>
                영상에서 느껴지는 정서를 가장 잘 나타내는 위치를 선택해 주세요.<br>
                각 문항은 <b>1점부터 9점</b>까지 응답할 수 있습니다.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    form_key = f"survey_form_{round_number}"
    with st.form(form_key):
        valence = vad_question(
            "1. 쾌락",
            "현재 감정 상태를 가장 잘 나타내는 위치를 선택해 주세요.",
            "V.png",
            "더 행복함",
            "더 불행함",
            f"vad_valence_{round_number}",
        )
        arousal = vad_question(
            "2. 각성",
            "현재 각성 수준을 가장 잘 나타내는 위치를 선택해 주세요.",
            "A.png",
            "더 각성됨",
            "더 차분함",
            f"vad_arousal_{round_number}",
        )
        dominance = vad_question(
            "3. 통제",
            "현재 통제감을 가장 잘 나타내는 위치를 선택해 주세요.",
            "D.png",
            "더 무력함",
            "더 통제감 있음",
            f"vad_dominance_{round_number}",
        )

        submitted = st.form_submit_button("다음", type="primary")

    if submitted:
        if valence is None or arousal is None or dominance is None:
            st.error("세 문항 모두 선택해 주세요.")
            return

        save_response(
            {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "participant_id": st.session_state.participant_id,
                "round_number": round_number,
                "block_number": current_block_number(st.session_state.round_index),
                "video_key": video["key"],
                "drive_file_id": video["file_id"],
                "vad_valence": valence,
                "vad_arousal": arousal,
                "vad_dominance": dominance,
            }
        )

        st.session_state.round_index += 1
        completed_round = st.session_state.round_index

        if st.session_state.round_index >= len(video_items):
            go_to("finish")

        # oTree 코드 기준: 25, 50, 75번째 영상 뒤 쉬는 시간
        if completed_round % get_sets_per_block() == 0:
            go_to("break")

        go_to("video")


def page_break(video_items: list):
    completed_round = st.session_state.round_index
    block_number = completed_round // get_sets_per_block()
    next_block_number = block_number + 1

    st.markdown(
        f"""
        <div class="warning-card">
            <div class="center-title">잠시 대기해 주세요</div>
            <div class="body-text">
                {block_number}번째 블록이 끝났습니다.<br>
                잠시 쉬는 시간을 가진 뒤 다음 블록을 진행합니다.<br>
                연구 진행자 지시가 있기 전까지는 조용히 대기해 주세요.
            </div>
            <div class="warning-red">
                연구 진행자의 지시가 있기 전까지는<br>
                다음 버튼을 누르지 마세요.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button(f"{next_block_number}번째 블록으로 이동", type="primary"):
        if st.session_state.round_index < len(video_items):
            go_to("block_start")
        else:
            go_to("finish")


def page_finish():
    st.markdown(
        """
        <div class="main-card" style="text-align:center;">
            <div class="center-title">실험이 종료되었습니다</div>
            <div class="body-text">
                참여해 주셔서 감사합니다.<br>
                연구 진행자의 안내를 기다려 주세요.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 연구자 로컬 확인용입니다. 실제 배포에서는 관리자만 접근하도록 따로 분리하는 것이 좋습니다.
    if RESPONSE_CSV.exists():
        with RESPONSE_CSV.open("rb") as f:
            st.download_button(
                "응답 CSV 다운로드",
                data=f,
                file_name="responses.csv",
                mime="text/csv",
            )


# =========================
# 앱 실행부
# =========================
def main():
    video_items = get_video_items_from_secrets()

    if not video_items:
        page_missing_secrets()
        return

    if "started" not in st.session_state:
        st.session_state.started = False

    if not st.session_state.started:
        page_participant_start(video_items)
        return

    page = st.session_state.get("page", "experiment_info")

    if page == "experiment_info":
        page_experiment_info()
    elif page == "block_start":
        page_block_start()
    elif page == "video":
        page_video(video_items)
    elif page == "survey":
        page_survey(video_items)
    elif page == "break":
        page_break(video_items)
    elif page == "finish":
        page_finish()
    else:
        st.session_state.page = "experiment_info"
        st.rerun()


if __name__ == "__main__":
    main()
