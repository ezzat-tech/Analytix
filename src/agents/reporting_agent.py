"""Reporting Agent - natural language summaries and export."""

from typing import Any, Optional
from datetime import datetime
from pathlib import Path

from .base_agent import BaseAgent, AgentResult


class ReportingAgent(BaseAgent):
    """
    Agent responsible for generating reports and summaries.

    Produces:
    - Natural language data summaries
    - Key findings from analysis
    - Export-ready reports (Markdown, HTML)

    Uses LLM for generating insightful narratives.
    """

    def __init__(self, llm_client: Optional[Any] = None, use_llm: bool = True, output_dir: str = "./outputs"):
        super().__init__("reporting", llm_client, use_llm)
        self.capabilities = ["summary", "findings", "export_markdown", "export_html"]
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def execute(self, context: Any, report_format: str = "markdown") -> AgentResult:
        """
        Generate comprehensive analysis report.

        Args:
            context: Shared session context with profile, analysis, and viz data
            report_format: "markdown" or "html"

        Returns:
            AgentResult with report content
        """
        try:
            # Gather all available data
            profile = context.data_profile or {}
            analysis = context.analysis_results or {}
            visualizations = context.visualizations or []
            data_source = context.data_source or "Unknown"

            if self.use_llm:
                # Generate report using LLM
                report = await self._generate_llm_report(context)
            else:
                # Use template-based report
                report = self._generate_template_report(profile, analysis, visualizations, data_source)

            context.report = report

            # Save report to file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = self.output_dir / f"report_{timestamp}.md"
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(report)

            return AgentResult(
                success=True,
                data=report,
                metadata={"report_path": str(report_path)}
            )

        except Exception as e:
            return AgentResult(success=False, error=f"Reporting error: {str(e)}")

    async def _generate_llm_report(self, context: Any) -> str:
        """Generate report using LLM for better narrative."""
        try:
            # Prepare data summary for LLM
            data_summary = {
                "source": context.data_source,
                "profile": context.data_profile,
                "analysis": context.analysis_results,
                "visualizations": context.visualizations,
                "errors": context.errors,
            }

            prompt = f"""Generate a comprehensive data analysis report based on this information:

{data_summary}

The report should include:
1. Executive summary (2-3 sentences)
2. Dataset overview (rows, columns, quality)
3. Key findings from analysis
4. Notable patterns or correlations
5. Data quality concerns
6. Recommendations for next steps

Format as Markdown with clear headings.
"""
            # LLMClient.generate() is synchronous, no await needed
            report = self.llm.generate(prompt, system=self.skills, temperature=0.3)
            return f"# Data Analysis Report\n\n*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n{report}"

        except Exception as e:
            # Fallback to template
            return self._generate_template_report(
                context.data_profile,
                context.analysis_results,
                context.visualizations,
                context.data_source
            )

    def _generate_template_report(
        self,
        profile: dict,
        analysis: dict,
        visualizations: list,
        data_source: str
    ) -> str:
        """Generate report using predefined template."""
        lines = []

        # Header
        lines.append("# Data Analysis Report")
        lines.append(f"\n*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        lines.append(f"\n**Data Source:** `{data_source}`")

        # Dataset Overview
        if profile:
            lines.append("\n---\n")
            lines.append("## Dataset Overview\n")
            lines.append(f"- **Rows:** {profile.get('row_count', 'N/A'):,}")
            lines.append(f"- **Columns:** {profile.get('column_count', 'N/A')}")
            lines.append(f"- **Memory:** {profile.get('memory_mb', 'N/A')} MB")

            # Quality summary
            quality = profile.get("quality_summary", {})
            if quality:
                lines.append(f"- **Completeness:** {quality.get('completeness_pct', 'N/A')}%")
                lines.append(f"- **Missing Values:** {quality.get('total_missing', 'N/A'):,} cells")

        # Column Details
        if profile and "columns" in profile:
            lines.append("\n---\n")
            lines.append("## Column Details\n")

            for col, info in list(profile["columns"].items())[:10]:  # Limit to 10 columns
                lines.append(f"### `{col}`")
                lines.append(f"- **Type:** {info.get('dtype', 'N/A')}")
                lines.append(f"- **Missing:** {info.get('missing_pct', 'N/A')}%")
                lines.append(f"- **Unique Values:** {info.get('unique', 'N/A')}")

                if "min" in info and info["min"] is not None:
                    lines.append(f"- **Range:** {info['min']} to {info['max']}")
                    if "mean" in info:
                        lines.append(f"- **Mean:** {info.get('mean', 'N/A')}")

                lines.append("")

        # Key Findings from Analysis
        if analysis:
            lines.append("\n---\n")
            lines.append("## Key Findings\n")

            if "descriptive" in analysis:
                lines.append("### Descriptive Statistics\n")
                lines.append("Statistics computed for all numeric columns.\n")

            if "correlation" in analysis:
                corr = analysis["correlation"]
                if "strong_correlations" in corr and corr["strong_correlations"]:
                    lines.append("### Strong Correlations\n")
                    for corr_item in corr["strong_correlations"][:5]:
                        pair = corr_item["pair"]
                        val = corr_item["correlation"]
                        strength = corr_item["strength"]
                        lines.append(f"- **{pair[0]}** ↔ **{pair[1]}**: {val} ({strength})")
                    lines.append("")

            if "insights" in analysis:
                lines.append("### Analysis Insights\n")
                for insight in analysis["insights"]:
                    lines.append(f"- {insight}")
                lines.append("")

        # Visualizations
        if visualizations:
            lines.append("\n---\n")
            lines.append("## Visualizations\n")
            for viz_path in visualizations:
                lines.append(f"- ![]({viz_path})")

        # Recommendations
        lines.append("\n---\n")
        lines.append("## Recommendations\n")
        lines.extend(self._generate_recommendations(profile, analysis))

        return "\n".join(lines)

    def _generate_recommendations(self, profile: dict, analysis: dict) -> list:
        """Generate data-driven recommendations."""
        recs = []

        # Check for high missingness
        if profile and "columns" in profile:
            high_missing = [
                col for col, info in profile["columns"].items()
                if info.get("missing_pct", 0) > 20
            ]
            if high_missing:
                recs.append(f"- **Address missing data:** Columns with >20% missing: {', '.join(high_missing)}")

        # Check for strong correlations
        if analysis and "correlation" in analysis:
            strong_corrs = analysis["correlation"].get("strong_correlations", [])
            if strong_corrs:
                recs.append("- **Investigate correlations:** Several strongly correlated pairs detected - consider multicollinearity in models")

        # Check for outliers
        if analysis and "outliers" in analysis:
            outlier_info = analysis["outliers"]
            if outlier_info.get("total_outliers_detected", 0) > 0:
                recs.append(f"- **Review outliers:** {outlier_info['total_outliers_detected']} potential outliers detected")

        # Default recommendations
        if not recs:
            recs.append("- Data appears clean - proceed with modeling or deeper analysis")
            recs.append("- Consider feature engineering based on column relationships")

        return recs

    async def export_html(self, context: Any) -> AgentResult:
        """Export report as HTML."""
        try:
            if not context.report:
                return AgentResult(success=False, error="No report generated yet")

            # Simple Markdown to HTML conversion
            html_content = context.report
            html_content = html_content.replace("# ", "<h1>", 1).replace("\n", "</h1>\n", 1)
            html_content = html_content.replace("## ", "<h2>", 1).replace("\n", "</h2>\n", 1)
            html_content = html_content.replace("### ", "<h3>", 1).replace("\n", "</h3>\n", 1)
            html_content = html_content.replace("**", "<b>", 1).replace("**", "</b>", 1)

            html_wrapper = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Data Analysis Report</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 900px; margin: 40px auto; padding: 20px; }}
        img {{ max-width: 100%; height: auto; }}
        code {{ background: #f4f4f4; padding: 2px 6px; border-radius: 3px; }}
        h1, h2, h3 {{ color: #333; }}
    </style>
</head>
<body>
{html_content}
</body>
</html>"""

            html_path = self.output_dir / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_wrapper)

            return AgentResult(
                success=True,
                data=str(html_path),
                metadata={"html_path": str(html_path)}
            )

        except Exception as e:
            return AgentResult(success=False, error=f"HTML export error: {str(e)}")

    async def generate_executive_summary(self, context: Any) -> AgentResult:
        """
        Generate a brief executive summary using LLM.

        Args:
            context: Session context

        Returns:
            AgentResult with 2-3 sentence summary
        """
        if not self.use_llm:
            return AgentResult(
                success=False,
                error="LLM required for executive summary generation"
            )

        try:
            data_summary = {
                "profile": context.data_profile,
                "analysis": context.analysis_results,
            }

            prompt = f"""Write a 2-3 sentence executive summary of this data analysis:

{data_summary}

Focus on the most important finding or insight.
"""
            summary = self.llm.generate(prompt, system=self.skills, max_tokens=150)

            return AgentResult(
                success=True,
                data=summary,
                metadata={"type": "executive_summary"}
            )

        except Exception as e:
            return AgentResult(success=False, error=str(e))
