from typing import Any, Dict, List

from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import time
from urllib.parse import quote_plus

from company_parser import parse_companies_from_element
from html_request import scrape_webpage


def scrape_companies(
    query: str,
    *,
    page_count: int = 1,
    max_retries: int = 2,
    verbose: bool = False,
    page_delay_seconds: float = 2.0,
) -> Dict[str, Any]:
    """Scrape company information for the given query.

    Returns a dictionary containing the scraped companies along with metadata.
    """

    def _log(message: str) -> None:
        if verbose:
            print(message)

    safe_query = quote_plus(query)

    def _build_urls(total_pages: int) -> List[str]:
        total_pages = max(1, total_pages)
        base_url = f"https://ensun.io/search?threshold=VERY_LOW&q={safe_query}"
        if total_pages == 1:
            return [base_url]
        return [base_url] + [f"{base_url}&page={page}" for page in range(2, total_pages + 1)]

    urls = _build_urls(page_count)
    _log(f"准备爬取 {len(urls)} 个URL: {urls}")

    all_companies: List[Dict[str, Any]] = []
    metadata: Dict[str, Any] = {
        "query": query,
        "urls": urls,
        "url": urls[0],
        "pages_requested": len(urls),
        "title": "",
        "error": None,
    }

    page_errors: List[str] = []

    def _scrape_with_retry(target_url: str) -> Dict[str, Any]:
        last_error = "页面爬取失败"
        for attempt in range(1, max_retries + 2):
            time.sleep(page_delay_seconds)
            result = scrape_webpage(target_url)
            if result.get("success") and result.get("html"):
                return result

            last_error = result.get("error") or last_error
            _log(
                f"❌ 页面爬取失败 (尝试 {attempt}/{max_retries + 1}): {last_error}"
            )

            if attempt <= max_retries:
                wait_seconds = max(page_delay_seconds, 2 * attempt)
                _log(f"⏳ {wait_seconds} 秒后重试...")
                time.sleep(wait_seconds)

        return {"success": False, "error": last_error, "url": target_url}

    for index, url in enumerate(urls, start=1):
        if index > 1:
            time.sleep(page_delay_seconds)
        _log(f"▶️ 正在处理第 {index} 页: {url}")
        page_result = _scrape_with_retry(url)
        if not page_result.get("success"):
            error_message = page_result.get("error") or "页面爬取失败"
            page_errors.append(f"第 {index} 页: {error_message}")
            _log(f"❌ 第 {index} 页抓取失败: {error_message}")
            continue

        try:
            soup = BeautifulSoup(page_result.get("html", ""), "html.parser")
        except Exception as parse_error:  # pragma: no cover - defensive
            page_errors.append(f"第 {index} 页解析HTML失败: {parse_error}")
            _log(f"❌ 第 {index} 页解析失败: {parse_error}")
            continue

        if index == 1:
            title_elements = soup.find_all(
                class_="MuiTypography-root MuiTypography-h4 mui-1kqqnff"
            )
            if title_elements:
                metadata["title"] = title_elements[0].get_text().strip()
                _log(f"标题: {metadata['title']}")

        elements = soup.find_all(class_="MuiStack-root mui-1yxbse7")
        if not elements:
            _log(
                "❌ 未找到包含 'MuiStack-root mui-1yxbse7' 类的元素，尝试重新加载页面..."
            )
            reload_result = _scrape_with_retry(url)
            if reload_result.get("success"):
                soup = BeautifulSoup(reload_result.get("html", ""), "html.parser")
                elements = soup.find_all(class_="MuiStack-root mui-1yxbse7")

        if not elements:
            message = "重新加载后仍未找到公司卡片"
            page_errors.append(f"第 {index} 页: {message}")
            _log(f"❌ 第 {index} 页 {message}")
            continue

        page_companies: List[Dict[str, Any]] = []
        for element in elements:
            page_companies.extend(parse_companies_from_element(element))

        if not page_companies:
            page_errors.append(f"第 {index} 页: 未能解析到公司信息")
            _log(f"❌ 第 {index} 页未解析到公司信息")
            continue

        all_companies.extend(page_companies)
        _log(f"✅ 第 {index} 页解析到 {len(page_companies)} 家公司")

    metadata["companies_count"] = len(all_companies)
    metadata["pages_succeeded"] = len(urls) - len(page_errors)
    if page_errors:
        metadata["error"] = "部分页面解析失败"
        metadata["page_errors"] = page_errors

    if not all_companies:
        metadata["error"] = metadata.get("error") or "未找到公司数据"

    return {"companies": all_companies, **metadata}


def export_to_excel(companies: List[Dict[str, Any]], filename: str = None) -> str:  # type: ignore
    """
    将公司数据导出到Excel文件
    
    Args:
        companies: 公司信息列表
        filename: 输出文件名（可选）
        
    Returns:
        str: 生成的文件路径
    """
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"tokenization_germany_companies_{timestamp}.xlsx"
    
    try:
        # 创建DataFrame
        df = pd.DataFrame(companies)
        
        # 导出到Excel
        df.to_excel(filename, index=False, engine='openpyxl')
        
        return filename
        
    except Exception as e:
        print(f"导出到Excel时出错: {e}")
        return ""


def main():
    """测试函数"""
    query = "Tokenization"

    result = scrape_companies(query, verbose=True)

    all_companies = result.get("companies", [])

    if not all_companies:
        print(f"❌ 未能解析到任何公司信息: {result.get('error', '未知错误')}")
        return

    print("\n" + "=" * 60)
    print(f"总计解析到 {len(all_companies)} 家公司，准备导出到Excel")
    print("=" * 60)

    for i, company in enumerate(all_companies, 1):
        print(f"\n{i}. {company['Company Name']}")
        print(f"   位置: {company['Location']}")
        print(f"   员工规模: {company['Employee']}")
        print(f"   成立年份: {company['Founding Year']}")
        print(f"   ESG国家风险: {company['ESG Country Risk']}")
        print(f"   描述: {company['Description'][:100]}...")

    filename = export_to_excel(all_companies)
    if filename:
        print(f"\n✅ 成功导出到Excel文件: {filename}")
    else:
        print("\n❌ Excel导出失败")


if __name__ == "__main__":
    main()
