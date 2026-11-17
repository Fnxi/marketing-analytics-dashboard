"""Compact presentation tables for performance summaries."""

from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

from src.components.formatters import format_metric


def render_performance_table(title: str, data: pd.DataFrame, columns: list[tuple[str, str, str]], height: int = 260) -> None:
    """Render a compact, light HTML performance table without dataframe clipping."""
    st.markdown(f"<h3 class='section-title'>{title}</h3>", unsafe_allow_html=True)
    header = "".join(f"<th>{escape(label)}</th>" for _, label, _ in columns)
    rows: list[str] = []
    for row in data.loc[:, [source for source, _, _ in columns]].itertuples(index=False, name=None):
        cells: list[str] = []
        for (source, _, metric), value in zip(columns, row, strict=True):
            content = format_metric(float(value), metric) if metric else str(value)
            css_class = " metric-highlight" if source in {"impressions", "ctr"} else ""
            cells.append(f"<td class='{css_class.strip()}'>{escape(content)}</td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")
    st.markdown(
        f"<div class='performance-table' style='max-height:{height}px'><table><thead><tr>{header}</tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></div>",
        unsafe_allow_html=True,
    )
