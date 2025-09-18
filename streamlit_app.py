"""Streamlit UI for searching ensun companies and exporting results."""

from __future__ import annotations

from io import BytesIO
import importlib.util
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st


def _load_scrape_companies() -> Any:
    module_path = Path(__file__).with_name("web-scraping.py")
    spec = importlib.util.spec_from_file_location("web_scraping_dynamic", module_path)
    if spec is None or spec.loader is None:
        raise ImportError("无法加载爬虫模块 web-scraping.py")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    try:
        return getattr(module, "scrape_companies")
    except AttributeError as exc:  # pragma: no cover - defensive
        raise ImportError("web-scraping.py 中缺少 scrape_companies 函数") from exc


scrape_companies = _load_scrape_companies()


st.set_page_config(page_title="ensun Unternehmenssuche", page_icon="🔍", layout="wide")
st.title("🔍 ensun Unternehmenssuche")


def _init_session_state() -> None:
    if "companies_df" not in st.session_state:
        st.session_state["companies_df"] = None
    if "scrape_error" not in st.session_state:
        st.session_state["scrape_error"] = None
    if "last_query" not in st.session_state:
        st.session_state["last_query"] = "Tokenization"
    if "last_page_count" not in st.session_state:
        st.session_state["last_page_count"] = 8
    if "scrape_metadata" not in st.session_state:
        st.session_state["scrape_metadata"] = {}
    if "last_page_delay" not in st.session_state:
        st.session_state["last_page_delay"] = 4.5


def _dataframe_to_excel_bytes(df: pd.DataFrame) -> bytes:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    buffer.seek(0)
    return buffer.read()


def _handle_submit(query: str, page_count: int, page_delay: float) -> None:
    cleaned_query = query.strip()
    if not cleaned_query:
        st.session_state["companies_df"] = None
        st.session_state["scrape_error"] = "Bitte geben Sie ein Suchwort ein."
        st.session_state["scrape_metadata"] = {}
        return

    pages_to_fetch = max(1, int(page_count))
    delay_seconds = max(0.0, float(page_delay))

    with st.spinner("Unternehmensdaten werden geladen …"):
        result: Dict[str, Any] = scrape_companies(
            cleaned_query,
            page_count=pages_to_fetch,
            verbose=False,
            page_delay_seconds=delay_seconds,
        )

    companies: List[Dict[str, Any]] = result.get("companies", [])
    st.session_state["last_query"] = cleaned_query
    st.session_state["last_page_count"] = pages_to_fetch
    st.session_state["last_page_delay"] = delay_seconds
    st.session_state["scrape_metadata"] = result

    if not companies:
        st.session_state["companies_df"] = None
        st.session_state["scrape_error"] = result.get("error") or "Keine Unternehmensdaten gefunden."
        return

    st.session_state["companies_df"] = pd.DataFrame(companies)
    st.session_state["scrape_error"] = None


def main() -> None:
    _init_session_state()

    with st.form("search_form", clear_on_submit=False):
        query = st.text_input(
            "Suchbegriff eingeben",
            value=st.session_state.get("last_query", ""),
            placeholder="Zum Beispiel: Tokenization",
        )
        page_count = st.number_input(
            "Seitenanzahl",
            min_value=1,
            max_value=50,
            value=st.session_state.get("last_page_count", 1),
            step=1,
        )
        page_delay = st.number_input(
            "Wartezeit pro Seite (Sekunden)",
            min_value=0.0,
            max_value=10.0,
            value=float(st.session_state.get("last_page_delay", 2.0)),
            step=0.5,
        )
        submitted = st.form_submit_button("Suchen")

    if submitted:
        _handle_submit(query, int(page_count), float(page_delay))

    error_message = st.session_state.get("scrape_error")
    if error_message:
        st.error(error_message)
        return

    companies_df: Optional[pd.DataFrame] = st.session_state.get("companies_df")
    if companies_df is None:
        st.info("Bitte Suchbegriff eingeben und auf Suchen klicken, um Unternehmen anzuzeigen.")
        return

    metadata = st.session_state.get("scrape_metadata", {})
    if metadata.get("title"):
        st.markdown(f"**{metadata['title']}**")
    elif metadata.get("companies_count"):
        st.markdown(
            f"**{metadata['companies_count']} Unternehmen gefunden – Suchbegriff: {st.session_state.get('last_query', '')}**"
        )

    page_errors: List[str] = metadata.get("page_errors", [])  # type: ignore[assignment]
    if page_errors:
        st.warning("Einige Seiten konnten nicht verarbeitet werden:\n" + "\n".join(page_errors))

    if metadata.get("pages_requested"):
        st.caption(
            f"Angefragt: {metadata.get('pages_requested')} Seiten · Erfolgreich: {metadata.get('pages_succeeded', metadata.get('pages_requested'))}"
        )

    st.dataframe(companies_df, width="stretch")

    excel_bytes = _dataframe_to_excel_bytes(companies_df)
    filename_query = st.session_state.get("last_query", "query").replace(" ", "_")
    st.download_button(
        label="Excel herunterladen",
        data=excel_bytes,
        file_name=f"ensun_companies_{filename_query}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


if __name__ == "__main__":
    main()
