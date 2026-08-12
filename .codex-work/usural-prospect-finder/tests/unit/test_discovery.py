from usural_prospect_finder.config import PROJECT_ROOT, load_category_config, load_yaml
from usural_prospect_finder.discovery import DomainClassification
from usural_prospect_finder.discovery.classification import classify_result
from usural_prospect_finder.discovery.queries import build_query_plan
from usural_prospect_finder.providers.search import SearchResult


def test_lawyer_query_plan_is_localized_and_configuration_driven() -> None:
    plan = build_query_plan("Lawyers", "Barcelona", load_category_config())
    texts = [query.text for query in plan.queries]
    assert "law firm Barcelona" in texts
    assert "abogados mercantiles Barcelona" in texts
    assert "despatx d'advocats Barcelona" in texts
    assert {query.locale for query in plan.queries} == {"en", "es", "ca"}
    assert len(texts) == len(set(text.casefold() for text in texts))


def test_query_plan_works_for_other_configured_category() -> None:
    plan = build_query_plan("dentists", "München", load_category_config())
    assert any("München" in query.text for query in plan.queries)


def test_classification_uses_domains_text_paths_and_metadata() -> None:
    exclusions = load_yaml(PROJECT_ROOT / "config/exclusions.yaml")
    cases = [
        (SearchResult("Studio Legal", "https://studio.example/", 1), DomainClassification.COMPANY),
        (SearchResult("Profile", "https://yelp.com/biz/x", 1), DomainClassification.DIRECTORY),
        (SearchResult("Council", "https://city.gov/legal", 1), DomainClassification.GOVERNMENT),
        (SearchResult("Report", "https://example.com/report.pdf", 1), DomainClassification.UNKNOWN),
        (
            SearchResult("Legal news", "https://paper.example/", 1, metadata={"type": "news"}),
            DomainClassification.NEWS,
        ),
    ]
    assert [classify_result(result, exclusions).classification for result, _ in cases] == [
        expected for _, expected in cases
    ]


def test_known_legal_platform_domains_are_excluded() -> None:
    exclusions = load_yaml(PROJECT_ROOT / "config/exclusions.yaml")
    expected = {
        "bestlawyers.com": DomainClassification.DIRECTORY,
        "chambers.com": DomainClassification.RANKING,
        "bestlawfirms.com": DomainClassification.RANKING,
        "legal500.com": DomainClassification.RANKING,
        "bcgsearch.com": DomainClassification.RECRUITMENT,
        "primerus.com": DomainClassification.NETWORK,
    }
    for domain, classification in expected.items():
        result = classify_result(SearchResult("Legal result", f"https://{domain}/", 1), exclusions)
        assert result.classification is classification
        assert result.confidence == 0.99
        assert result.reasons


def test_layered_legal_platform_signals_are_explainable() -> None:
    exclusions = load_yaml(PROJECT_ROOT / "config/exclusions.yaml")
    cases = [
        (
            SearchResult(
                "Lawyer directory",
                "https://independent.example/",
                1,
                "Find a lawyer from thousands of lawyers",
            ),
            DomainClassification.DIRECTORY,
        ),
        (
            SearchResult(
                "Research and rankings",
                "https://guide.example/",
                1,
                "Leading lawyers and law firm rankings",
            ),
            DomainClassification.RANKING,
        ),
        (
            SearchResult(
                "International network",
                "https://members.example/",
                1,
                "Find a member among member firms",
            ),
            DomainClassification.NETWORK,
        ),
        (
            SearchResult(
                "Legal recruitment",
                "https://talent.example/",
                1,
                "Attorney jobs from an executive search firm",
            ),
            DomainClassification.RECRUITMENT,
        ),
        (
            SearchResult(
                "Legal marketplace",
                "https://match.example/",
                1,
                "Compare lawyers and get matched",
            ),
            DomainClassification.MARKETPLACE,
        ),
    ]
    for search_result, classification in cases:
        result = classify_result(search_result, exclusions)
        assert result.classification is classification
        assert result.confidence >= 0.80
        assert len(result.reasons) >= 2


def test_category_hints_preserve_genuine_law_firms_and_reject_ambiguous_results() -> None:
    exclusions = load_yaml(PROJECT_ROOT / "config/exclusions.yaml")
    hints = load_category_config()["lawyers"]["classification_hints"]
    genuine_domains = {
        "cuatrecasas.com": "Law firm in Barcelona | Cuatrecasas",
        "garrigues.com": "Despacho de abogados en Barcelona | Garrigues",
        "uria.com": "Lawyers Barcelona | Uría Menéndez",
        "agmabogados.com": "AGM Abogados: Bufete de abogados en Barcelona",
        "freixaadvocats.com": "Despatx d'Advocats a Barcelona",
    }
    for domain, title in genuine_domains.items():
        result = classify_result(SearchResult(title, f"https://{domain}/", 1), exclusions, hints)
        assert result.classification is DomainClassification.COMPANY
        assert result.confidence >= 0.80
        assert any("category company term" in reason for reason in result.reasons)

    ambiguous = classify_result(
        SearchResult("Smith & Partners", "https://smithpartners.example/", 1), exclusions, hints
    )
    assert ambiguous.classification is DomainClassification.UNKNOWN
    assert ambiguous.reasons == ("insufficient category-specific company evidence",)


def test_single_ambiguous_platform_word_does_not_override_firm_page_evidence() -> None:
    exclusions = load_yaml(PROJECT_ROOT / "config/exclusions.yaml")
    hints = load_category_config()["lawyers"]["classification_hints"]
    result = classify_result(
        SearchResult(
            "Spain",
            "https://internationalfirm.example/people_and_places/spain",
            1,
            "Recent rankings for our Spain office",
        ),
        exclusions,
        hints,
    )
    assert result.classification is DomainClassification.COMPANY
    assert any("path contains category company term" in reason for reason in result.reasons)


def test_high_confidence_aggregator_language_outweighs_company_terms() -> None:
    exclusions = load_yaml(PROJECT_ROOT / "config/exclusions.yaml")
    hints = load_category_config()["lawyers"]["classification_hints"]
    result = classify_result(
        SearchResult(
            "English-speaking lawyers",
            "https://city-guide.example/lawyers",
            1,
            "A directory of lawyers and law firms offering detailed profiles.",
        ),
        exclusions,
        hints,
    )
    assert result.classification is DomainClassification.DIRECTORY
    assert result.confidence >= 0.88
