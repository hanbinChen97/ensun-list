"""Parse company cards from ensun search result pages."""

from __future__ import annotations

from typing import Any, Dict, List
from urllib.parse import urljoin


def parse_single_company_card(paper) -> Dict[str, Any]:
    """Parse a single company card element and return company information dictionary."""
    company_info: Dict[str, Any] = {}
    
    name_element = paper.select_one(
        "p.MuiTypography-root.MuiTypography-body1.mui-1e9jes1"
    )
    if name_element and name_element.get_text(strip=True):
        company_info["Company Name"] = name_element.get_text(strip=True)

    info_elements = paper.select(
        "p.MuiTypography-root.MuiTypography-body1.mui-98jxju"
    )
    for info_elem in info_elements:
        text = info_elem.get_text(strip=True)
        if not text:
            continue

        if "Employees" in text:
            company_info["Employee"] = text.replace(" Employees", "")
            continue

        if text.isdigit() and len(text) == 4:
            company_info["Founding Year"] = text
            continue

        if not company_info.get("Location"):
            company_info["Location"] = text

    esg_element = paper.select_one(
        "p.MuiTypography-root.MuiTypography-body1.mui-dfcthu"
    )
    if esg_element and esg_element.get_text(strip=True):
        company_info["ESG Country Risk"] = esg_element.get_text(strip=True)

    link_element = paper.find("a", href=lambda href: href and "/company/" in href)
    if link_element and link_element.get("href"):
        company_info["Detail URL"] = urljoin("https://ensun.io", link_element.get("href"))
        if not company_info.get("Company Name"):
            link_text = link_element.get_text(strip=True)
            if link_text:
                company_info["Company Name"] = link_text

    # 描述信息
    desc_element = paper.find("p", class_=lambda x: x and "mui-1jyj4mb" in x)
    if desc_element:
        company_info["Description"] = desc_element.get_text().strip()

    return company_info


def parse_companies_from_element(element) -> List[Dict[str, Any]]:
    """Extract company information dictionaries from a given BeautifulSoup element."""
    companies: List[Dict[str, Any]] = []

    paper_elements = element.find_all(
        "div", class_=lambda x: x and "MuiPaper-root" in x and "mui-t3yxhx" in x
    )

    print(f"找到 {len(paper_elements)} 个公司卡片")

    skipped_cards = 0

    for i, paper in enumerate(paper_elements):
        company_info = parse_single_company_card(paper)

        if not company_info.get("Company Name"):
            skipped_cards += 1
            continue

        # 设置字段默认值，保持数据表结构一致
        company_info.setdefault("Location", "Unknown")
        company_info.setdefault("Employee", "Unknown")
        company_info.setdefault("Founding Year", "Unknown")
        company_info.setdefault("Description", "No description available")
        company_info.setdefault("ESG Country Risk", "Unknown")
        company_info.setdefault("Detail URL", "")

        print(
            "解析公司 {}: {} | 位置: {} | 员工: {} | 年份: {} | ESG风险: {}".format(
                len(companies) + 1,
                company_info.get("Company Name", f"Company {len(companies) + 1}"),
                company_info["Location"],
                company_info["Employee"],
                company_info["Founding Year"],
                company_info["ESG Country Risk"],
            )
        )

        companies.append(company_info)

    if skipped_cards:
        print(f"跳过未识别的公司卡片 {skipped_cards} 个")

    return companies


__all__ = ["parse_companies_from_element", "parse_single_company_card"]
