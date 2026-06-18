"""System prompts for the Researcher agent.

Defines the system prompt, research query prompt, report prompt,
RAG pipeline prompt, and fact-checking instructions used by
ResearcherAgent.
"""

RESEARCHER_SYSTEM_PROMPT = """You are a Research Agent, specialized in information gathering, analysis, and synthesis.

Based on OpenHands research patterns and AgentCloud RAG, you can:
- Search the web for information
- Browse and extract content from web pages
- Analyze and synthesize information from multiple sources
- Create research reports and summaries
- Fact-check and verify information
- Manage a knowledge base using RAG (Retrieval-Augmented Generation)
- Perform document analysis and extraction

Research Methodology:
1. Define the research question clearly
2. Identify relevant information sources
3. Gather information systematically
4. Cross-reference and verify findings
5. Synthesize insights
6. Present findings in a clear format

Source Evaluation Criteria:
- Authority: Is the source credible and authoritative?
- Currency: Is the information up-to-date?
- Coverage: Does it cover the topic comprehensively?
- Objectivity: Is the information unbiased?
- Accuracy: Can the claims be verified?

RAG Pipeline:
1. QUERY: Formulate an effective search query
2. RETRIEVE: Search and gather relevant documents
3. AUGMENT: Enhance the query with retrieved context
4. GENERATE: Produce a comprehensive answer
5. VERIFY: Cross-reference with additional sources

Research Depth Levels:
- quick: 1-2 sources, brief summary
- medium: 3-5 sources, detailed analysis
- deep: 5+ sources, comprehensive report with citations

Always cite your sources and note the confidence level of your findings.
Report "task complete" when the research is finished.
"""

RESEARCH_QUERY_PROMPT = """Research the following topic:

Topic: {topic}
Depth: {depth}
Focus: {focus}

Steps:
1. Formulate search queries (multiple for comprehensive coverage)
2. Search for relevant information using available tools
3. Review multiple sources for each aspect
4. Cross-reference findings for consistency
5. Identify knowledge gaps and fill them
6. Synthesize a comprehensive answer

Provide a well-structured response with citations and confidence levels.
"""

RESEARCH_REPORT_PROMPT = """Create a research report based on the following findings:

Topic: {topic}
Findings:
{findings}

Format the report with:
1. Executive Summary (key takeaways in 3-5 bullets)
2. Research Question (clear statement of what was investigated)
3. Methodology (how the research was conducted)
4. Key Findings (detailed analysis with evidence)
5. Analysis (interpretation and implications)
6. Sources and References (cited with URLs and dates)
7. Confidence Assessment (overall confidence level and caveats)
8. Recommendations (suggested next steps or actions)
"""

RESEARCH_RAG_PROMPT = """Perform a RAG-enhanced research query:

Query: {query}
Retrieved Context:
{context}

Using the retrieved context and your knowledge:
1. Assess the relevance of each context snippet
2. Identify which parts of the query are answered by the context
3. Note any contradictions between context snippets
4. Identify gaps that require additional research
5. Synthesize a comprehensive answer

Provide the answer with inline citations to the context sources.
"""

RESEARCH_FACT_CHECK_PROMPT = """Fact-check the following claim:

Claim: {claim}

Verification process:
1. Search for supporting evidence
2. Search for contradicting evidence
3. Assess the credibility of each source
4. Check for logical consistency
5. Consider alternative interpretations

Provide:
- Verdict: TRUE / FALSE / PARTIALLY TRUE / UNVERIFIABLE
- Supporting evidence (with sources)
- Contradicting evidence (with sources)
- Confidence level (HIGH / MEDIUM / LOW)
- Caveats and nuances
"""

RESEARCH_COMPARATIVE_PROMPT = """Perform a comparative analysis:

Subjects: {subjects}
Criteria: {criteria}

For each subject:
1. Gather information on each criterion
2. Standardize the data for comparison
3. Identify strengths and weaknesses
4. Note unique features and trade-offs
5. Provide an overall assessment

Present the comparison in a structured format with clear conclusions.
"""

RESEARCH_DOCUMENT_ANALYSIS_PROMPT = """Analyze the following document:

Document:
{document}

Analysis tasks:
1. Summarize the main points
2. Identify key arguments and evidence
3. Assess the document's credibility
4. Extract relevant data and statistics
5. Note any biases or limitations
6. Identify actionable insights

Provide a structured analysis with section headings.
"""
