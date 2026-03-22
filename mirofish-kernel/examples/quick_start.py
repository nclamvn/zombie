"""
MiroFish Kernel — Quick Start Example

Shows how to use the kernel for a complete prediction pipeline.

Prerequisites:
    pip install mirofish-kernel[openai,zep,files]
    
    export LLM_API_KEY=your_openai_key
    export ZEP_API_KEY=your_zep_key
"""

import os
from core import PipelineOrchestrator
from adapters.llm.openai_adapter import OpenAIAdapter
from adapters.graph.zep_adapter import ZepGraphAdapter


def main():
    # ─── 1. Initialize adapters ────────────────────────────────
    llm = OpenAIAdapter(
        api_key=os.environ["LLM_API_KEY"],
        base_url=os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1"),
        model=os.environ.get("LLM_MODEL_NAME", "gpt-4o-mini"),
    )
    
    graph_store = ZepGraphAdapter(
        api_key=os.environ["ZEP_API_KEY"],
    )
    
    # ─── 2. Create pipeline ────────────────────────────────────
    pipeline = PipelineOrchestrator(
        llm=llm,
        graph_store=graph_store,
        # simulation_engine=OasisAdapter(),  # Optional: add for actual simulation
        # memory_store=ZepMemoryAdapter(),   # Optional: add for memory persistence
    )
    
    # ─── 3. Run full pipeline ──────────────────────────────────
    
    # Option A: From text
    result = pipeline.run(
        requirement="Predict public reaction to a new AI regulation policy",
        text="""
        The government announced a new AI regulation framework today.
        Key provisions include mandatory AI audits for companies with 
        more than 100 employees, transparency requirements for AI-driven 
        decisions, and a new AI Safety Board. Tech industry leaders 
        expressed mixed reactions...
        """,
        project_name="AI Regulation Impact",
        progress_callback=lambda msg, pct: print(f"[{pct:>6.1%}] {msg}"),
    )
    
    # Option B: From files
    # result = pipeline.run(
    #     requirement="Predict market impact of semiconductor export restrictions",
    #     file_paths=["report.pdf", "analysis.md"],
    # )
    
    # ─── 4. Access results ─────────────────────────────────────
    print("\n" + "=" * 60)
    print(f"Project: {result['project']['name']}")
    print(f"Graph: {result['graph_info']['node_count']} nodes, "
          f"{result['graph_info']['edge_count']} edges")
    print(f"Agents: {result['agent_count']}")
    print(f"\n📊 REPORT:\n{result['report'][:2000]}...")
    
    # ─── 5. Interactive chat ───────────────────────────────────
    project_id = result["project"]["project_id"]
    while True:
        question = input("\n❓ Ask about the report (or 'quit'): ")
        if question.lower() in ("quit", "exit", "q"):
            break
        answer = pipeline.chat_with_report(project_id, question)
        print(f"\n💡 {answer}")
    
    # ─── 6. Cleanup ────────────────────────────────────────────
    graph_store.delete_graph(result["graph_id"])
    print("\nDone! Graph cleaned up.")


def step_by_step_example():
    """
    Alternative: Step-by-step usage for more control.
    """
    from core.pipeline import (
        SeedProcessor,
        OntologyDesigner,
        GraphBuilder,
        ConfigGenerator,
        ProfileGenerator,
        RetrievalTools,
        ReportAgent,
    )
    
    llm = OpenAIAdapter(
        api_key=os.environ["LLM_API_KEY"],
        model="gpt-4o-mini",
    )
    graph_store = ZepGraphAdapter(api_key=os.environ["ZEP_API_KEY"])
    
    # Step 1: Process seed
    seed = SeedProcessor(chunk_size=500)
    seed_result = seed.process_text(
        "Your seed text here...",
        requirement="What will happen...",
    )
    
    # Step 2: Design ontology
    designer = OntologyDesigner(llm)
    ontology = designer.design(
        document_texts=[seed_result["raw_text"]],
        requirement=seed_result["requirement"],
    )
    print(f"Ontology: {ontology.entity_type_names}")
    
    # Step 3: Build graph
    builder = GraphBuilder(graph_store)
    result = builder.build(seed_result["chunks"], ontology)
    print(f"Graph: {result.graph_info.node_count} nodes")
    
    # Step 4: Generate config
    config_gen = ConfigGenerator(llm, graph_store)
    config = config_gen.generate(result.graph_id, seed_result["requirement"])
    
    # Step 5: Generate profiles
    profile_gen = ProfileGenerator(llm, graph_store)
    profiles = profile_gen.generate_profiles(
        result.graph_id, seed_result["requirement"]
    )
    print(f"Agents: {[p.name for p in profiles]}")
    
    # Step 6: Generate report (skip simulation for quick demo)
    retrieval = RetrievalTools(llm, graph_store)
    reporter = ReportAgent(llm, retrieval)
    
    report = reporter.generate_full_report(
        requirement=seed_result["requirement"],
        graph_id=result.graph_id,
        simulation_summary={
            "total_rounds": 0,
            "total_agents": len(profiles),
            "note": "Graph-only analysis (no simulation)",
        },
    )
    print(f"\n📊 Report:\n{report[:1000]}...")
    
    # Cleanup
    graph_store.delete_graph(result.graph_id)


if __name__ == "__main__":
    main()
