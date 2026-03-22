"""
MiroFish Kernel — Custom Domain Example

Shows how to use the kernel for non-social-media domains:
- Supply chain simulation (RTR SimEngine style)
- Social matching (CẦN & CÓ style)
- Financial prediction

The key: you can customize prompts and swap adapters.
"""

import os
from core import PipelineOrchestrator
from core.pipeline.ontology_designer import OntologyDesigner
from adapters.llm.openai_adapter import OpenAIAdapter
from adapters.graph.zep_adapter import ZepGraphAdapter


# ─── Example 1: Supply Chain Domain ──────────────────────────────

SUPPLY_CHAIN_ONTOLOGY_PROMPT = """You are a supply chain ontology designer. 
Design entity types and relationships for supply chain simulation.

Entity types should include: Supplier, Manufacturer, Distributor, Retailer, 
RawMaterial, Component, Product, Warehouse, TransportRoute.

Relationships: SUPPLIES_TO, MANUFACTURES, STORES_AT, TRANSPORTS_VIA, 
DEPENDS_ON, COMPETES_WITH, CONTRACTS_WITH.

Output valid JSON only."""


def supply_chain_example():
    """RTR SimEngine-style supply chain simulation."""
    llm = OpenAIAdapter(
        api_key=os.environ["LLM_API_KEY"],
        model="gpt-4o-mini",
    )
    graph_store = ZepGraphAdapter(api_key=os.environ["ZEP_API_KEY"])
    
    # Custom ontology prompt for supply chain domain
    designer = OntologyDesigner(llm, system_prompt=SUPPLY_CHAIN_ONTOLOGY_PROMPT)
    
    pipeline = PipelineOrchestrator(
        llm=llm,
        graph_store=graph_store,
    )
    
    # Override the ontology designer with custom prompt
    pipeline.ontology_designer = designer
    
    result = pipeline.run(
        requirement=(
            "Simulate supply chain disruption when a key semiconductor supplier "
            "faces a 30% capacity reduction. Predict impact on drone manufacturing "
            "timeline and identify alternative sourcing strategies."
        ),
        text="""
        RTR manufactures HERA and Vega drone systems requiring advanced semiconductors.
        Primary supplier: TSMC (Taiwan) - provides 65% of AI chips.
        Secondary supplier: Samsung (Korea) - provides 25%.
        Local supplier: VinSemi - provides 10% of basic components.
        
        HERA drone BOM includes: flight controller (TSMC chip), AI edge processor 
        (105 TOPS, TSMC), camera module (Sony), battery (CATL), frame (local).
        
        Current lead time: 12 weeks for TSMC components, 8 weeks Samsung, 2 weeks local.
        Inventory buffer: 6 weeks of TSMC chips, 4 weeks Samsung.
        """,
        project_name="RTR Supply Chain Disruption",
    )
    
    print(result["report"][:2000])


# ─── Example 2: Social Matching (CẦN & CÓ style) ────────────────

SOCIAL_MATCHING_PROMPT = """You are a marketplace ontology designer.
Design entity types for a supply-demand matching platform.

Entity types: Seeker (person who needs something), Provider (person who has something),
Need (a specific request), Offer (a specific thing available), Category, Location.

Relationships: HAS_NEED, HAS_OFFER, MATCHES_WITH, LOCATED_IN, BELONGS_TO_CATEGORY,
TRUSTS, VOUCHES_FOR.

Output valid JSON only."""


def social_matching_example():
    """CẦN & CÓ style intent-based social network simulation."""
    llm = OpenAIAdapter(
        api_key=os.environ["LLM_API_KEY"],
        model="gpt-4o-mini",
    )
    graph_store = ZepGraphAdapter(api_key=os.environ["ZEP_API_KEY"])
    
    designer = OntologyDesigner(llm, system_prompt=SOCIAL_MATCHING_PROMPT)
    
    pipeline = PipelineOrchestrator(llm=llm, graph_store=graph_store)
    pipeline.ontology_designer = designer
    
    result = pipeline.run(
        requirement=(
            "Simulate how a real estate matching platform performs when "
            "200 users post their needs and offers over 7 days. "
            "Predict match rate, time-to-match, and trust dynamics."
        ),
        text="""
        NHA.AI is a real estate matching platform in Ho Chi Minh City.
        Users post either "I NEED" (looking for apartment, office, etc.)
        or "I HAVE" (listing property). AI automatically matches based on
        location, price range, requirements, and trust scores.
        
        Current user base: 500 active users, 60% seekers, 40% providers.
        Average match rate: 23%. Average time to match: 4.2 days.
        Trust system: users verify via phone, reviews, and vouching.
        """,
        project_name="NHA.AI Matching Simulation",
    )
    
    print(result["report"][:2000])


if __name__ == "__main__":
    print("Choose example:")
    print("1. Supply Chain (RTR SimEngine)")
    print("2. Social Matching (CẦN & CÓ)")
    
    choice = input("> ")
    if choice == "1":
        supply_chain_example()
    elif choice == "2":
        social_matching_example()
