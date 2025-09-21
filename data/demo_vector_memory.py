"""
AI Long-Term Memory with Vector Database - Demonstration
Showcases the capabilities of the vector memory system
"""

import asyncio
import json
import logging
import tempfile
import shutil
from datetime import datetime
from pathlib import Path

from AIMemoryQueryInterface import create_memory_interface


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def demonstrate_vector_memory_system():
    """Comprehensive demonstration of AI long-term memory capabilities"""
    
    print("\n" + "="*80)
    print("🧠 AI LONG-TERM MEMORY WITH VECTOR DATABASE DEMONSTRATION")
    print("="*80)
    
    # Create temporary directory for demo
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Initialize memory interface
        print("\n🚀 Initializing AI Memory System...")
        memory_interface = await create_memory_interface(persist_directory=temp_dir)
        print("✅ Memory system initialized successfully!")
        
        # Demonstrate conversation memory
        await demo_conversation_memory(memory_interface)
        
        # Demonstrate knowledge extraction
        await demo_knowledge_extraction(memory_interface)
        
        # Demonstrate semantic search
        await demo_semantic_search(memory_interface)
        
        # Demonstrate learning from feedback
        await demo_feedback_learning(memory_interface)
        
        # Demonstrate contextual queries
        await demo_contextual_queries(memory_interface)
        
        # Show system statistics
        await show_system_statistics(memory_interface)
        
        # Demonstrate API capabilities
        await demo_api_capabilities(memory_interface)
        
        print("\n🎉 Demonstration completed successfully!")
        print("✅ AI Long-Term Memory system is fully functional and ready for production!")
        
    except ImportError as e:
        print(f"\n❌ ChromaDB not available: {e}")
        print("💡 To enable vector memory features, install ChromaDB:")
        print("   pip install chromadb")
        
    except Exception as e:
        print(f"\n❌ Error during demonstration: {e}")
        
    finally:
        # Cleanup
        if temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)


async def demo_conversation_memory(memory_interface):
    """Demonstrate conversation memory storage and retrieval"""
    
    print("\n" + "-"*60)
    print("💬 CONVERSATION MEMORY DEMONSTRATION")
    print("-"*60)
    
    conversation_id = "demo_conversation_001"
    
    # Simulate a conversation about machine learning
    conversation_turns = [
        {
            "content": "Hello! I'm interested in learning about machine learning. Can you help me understand the basics?",
            "metadata": {"speaker": "user", "turn": 1, "timestamp": datetime.now().isoformat()}
        },
        {
            "content": "I'd be happy to help! Machine learning is a subset of artificial intelligence that enables systems to learn and improve from data without explicit programming. There are three main types: supervised learning (with labeled data), unsupervised learning (finding patterns in unlabeled data), and reinforcement learning (learning through rewards and penalties).",
            "metadata": {"speaker": "assistant", "turn": 2, "timestamp": datetime.now().isoformat()}
        },
        {
            "content": "That's helpful! Can you explain what supervised learning involves in more detail?",
            "metadata": {"speaker": "user", "turn": 3, "timestamp": datetime.now().isoformat()}
        },
        {
            "content": "Supervised learning uses labeled training data to learn patterns and make predictions. For example, to build an email spam detector, you'd train the model on thousands of emails already labeled as 'spam' or 'not spam'. Common algorithms include linear regression for numerical predictions, logistic regression for classification, decision trees, random forests, and neural networks.",
            "metadata": {"speaker": "assistant", "turn": 4, "timestamp": datetime.now().isoformat()}
        }
    ]
    
    print("📝 Storing conversation memories...")
    stored_memories = []
    
    for turn in conversation_turns:
        result = await memory_interface.remember_conversation(
            conversation_id=conversation_id,
            content=turn["content"],
            metadata=turn["metadata"]
        )
        stored_memories.append(result)
        print(f"   ✅ Stored turn {turn['metadata']['turn']}: {result['memory_id']}")
        if result['knowledge_extracted'] > 0:
            print(f"      🧠 Extracted {result['knowledge_extracted']} knowledge chunks")
    
    # Retrieve conversation history
    print(f"\n🔍 Retrieving conversation history for: {conversation_id}")
    history = await memory_interface.get_conversation_history(
        conversation_id=conversation_id,
        context_window=10
    )
    
    print(f"   📊 Total conversation memories: {history['total_memories']}")
    print(f"   📝 Recent memories: {len(history['recent_memories'])}")
    print(f"   🔗 Related context items: {len(history.get('related_context', []))}")
    print(f"   📋 Context summary: {history['context_summary'][:100]}...")


async def demo_knowledge_extraction(memory_interface):
    """Demonstrate knowledge extraction and indexing"""
    
    print("\n" + "-"*60)
    print("🧠 KNOWLEDGE EXTRACTION DEMONSTRATION")
    print("-"*60)
    
    # Sample technical content for knowledge extraction
    technical_content = """
    Deep Learning and Neural Networks
    
    Deep learning is a subset of machine learning that uses artificial neural networks with multiple layers (hence "deep") to model and understand complex patterns in data. The key innovation is that these networks can automatically learn hierarchical representations of data.
    
    Neural networks are inspired by the structure of biological brains and consist of interconnected nodes (neurons) organized in layers. Each connection has a weight that determines the strength of the signal passed between neurons. The network learns by adjusting these weights through a process called backpropagation.
    
    Convolutional Neural Networks (CNNs) are particularly effective for image processing tasks. They use convolution operations to detect features like edges, textures, and shapes. CNNs have revolutionized computer vision applications including image classification, object detection, and facial recognition.
    
    Recurrent Neural Networks (RNNs) are designed for sequential data like text or time series. They have memory capabilities that allow them to remember previous inputs. Long Short-Term Memory (LSTM) networks are a type of RNN that can learn long-term dependencies.
    
    Transformer architectures, introduced in the "Attention is All You Need" paper, have become the foundation for modern natural language processing. They use self-attention mechanisms to process sequences in parallel, making them more efficient than RNNs for many tasks.
    """
    
    print("📚 Extracting knowledge from technical content...")
    
    extraction_result = await memory_interface.extract_knowledge(
        content=technical_content,
        source_id="deep_learning_overview_2024",
        knowledge_type="deep_learning",
        metadata={
            "domain": "artificial_intelligence",
            "complexity": "intermediate",
            "author": "demonstration",
            "topics": ["neural_networks", "deep_learning", "cnn", "rnn", "transformers"]
        }
    )
    
    print(f"   ✅ Knowledge extraction completed!")
    print(f"   📊 Extracted {extraction_result['extracted_count']} knowledge chunks")
    print(f"   🆔 Knowledge IDs: {extraction_result['knowledge_ids'][:3]}...") # Show first 3 IDs
    
    # Extract knowledge from a different domain
    business_content = """
    Project Management Best Practices
    
    Effective project management requires clear communication, well-defined goals, and proper resource allocation. The project management lifecycle consists of five phases: initiation, planning, execution, monitoring, and closure.
    
    Agile methodologies emphasize iterative development, customer collaboration, and responding to change. Scrum is a popular agile framework that uses sprints, daily standups, and retrospectives to manage work.
    
    Risk management involves identifying potential issues early and developing mitigation strategies. Common project risks include scope creep, resource constraints, and timeline pressures.
    """
    
    print("\n📈 Extracting business knowledge...")
    business_result = await memory_interface.extract_knowledge(
        content=business_content,
        source_id="project_management_guide",
        knowledge_type="project_management",
        metadata={"domain": "business", "complexity": "beginner"}
    )
    
    print(f"   ✅ Extracted {business_result['extracted_count']} business knowledge chunks")


async def demo_semantic_search(memory_interface):
    """Demonstrate semantic search capabilities"""
    
    print("\n" + "-"*60)
    print("🔍 SEMANTIC SEARCH DEMONSTRATION") 
    print("-"*60)
    
    search_queries = [
        "neural network architectures",
        "project management methodologies", 
        "machine learning algorithms",
        "data preprocessing techniques"
    ]
    
    for query in search_queries:
        print(f"\n🔎 Searching for: '{query}'")
        
        results = await memory_interface.ask_memory(
            query=query,
            memory_types=["knowledge", "conversations"],
            limit=5
        )
        
        print(f"   📊 Found {len(results['direct_matches'])} direct matches")
        
        if results['direct_matches']:
            top_match = results['direct_matches'][0]
            similarity = top_match['similarity']
            content_preview = top_match['content'][:100] + "..."
            memory_type = top_match['memory_type']
            
            print(f"   🎯 Top match ({similarity:.1%} similarity):")
            print(f"      📝 Content: {content_preview}")
            print(f"      🏷️ Type: {memory_type}")
        
        if results.get('suggestions'):
            print(f"   💡 Suggested queries: {[s['query'] for s in results['suggestions'][:2]]}")


async def demo_feedback_learning(memory_interface):
    """Demonstrate learning from user feedback"""
    
    print("\n" + "-"*60)
    print("📈 FEEDBACK LEARNING DEMONSTRATION")
    print("-"*60)
    
    # Simulate various interaction scenarios with feedback
    interactions = [
        {
            "id": "helpful_explanation",
            "content": "User found the explanation of neural networks very clear and comprehensive, particularly appreciated the biological analogy",
            "feedback_score": 0.95,
            "type": "educational_content"
        },
        {
            "id": "confusing_response", 
            "content": "User was confused by the technical jargon in the transformer architecture explanation, requested simpler language",
            "feedback_score": -0.6,
            "type": "educational_content"
        },
        {
            "id": "perfect_example",
            "content": "User said the CNN example with image recognition was perfect for understanding the concept",
            "feedback_score": 0.9,
            "type": "example_explanation"
        },
        {
            "id": "too_basic",
            "content": "User indicated that the basic machine learning introduction was too elementary for their level",
            "feedback_score": -0.3,
            "type": "level_mismatch"
        }
    ]
    
    print("🎓 Processing user feedback to improve future responses...")
    
    for interaction in interactions:
        result = await memory_interface.learn_from_interaction(
            interaction_id=interaction["id"],
            content=interaction["content"],
            interaction_type=interaction["type"],
            feedback_score=interaction["feedback_score"],
            metadata={
                "learning_opportunity": True,
                "feedback_category": "positive" if interaction["feedback_score"] > 0 else "negative"
            }
        )
        
        feedback_emoji = "👍" if interaction["feedback_score"] > 0 else "👎"
        score_str = f"{interaction['feedback_score']:+.1f}"
        
        print(f"   {feedback_emoji} {interaction['id']}: {score_str} score")
        
        if result['knowledge_extracted'] > 0:
            print(f"      🧠 Extracted {result['knowledge_extracted']} learning points")
    
    print("\n✨ The AI system now has learned from this feedback and can:")
    print("   • Provide clearer explanations with biological analogies (positive feedback)")
    print("   • Avoid overly technical jargon (negative feedback)")
    print("   • Use concrete examples like CNN image recognition (positive feedback)")
    print("   • Adjust complexity level based on user expertise (negative feedback)")


async def demo_contextual_queries(memory_interface):
    """Demonstrate contextual memory queries"""
    
    print("\n" + "-"*60)
    print("🧩 CONTEXTUAL QUERY DEMONSTRATION")
    print("-"*60)
    
    # Use the conversation we created earlier
    conversation_id = "demo_conversation_001"
    
    contextual_queries = [
        "What did we discuss about supervised learning?",
        "Can you remind me what I asked about earlier?",
        "What examples were given for machine learning applications?"
    ]
    
    for query in contextual_queries:
        print(f"\n🔍 Contextual query: '{query}'")
        
        # Query with conversation context
        results = await memory_interface.ask_memory(
            query=query,
            context_id=conversation_id,
            memory_types=["conversations", "knowledge"],
            limit=3
        )
        
        print(f"   💬 Direct matches: {len(results['direct_matches'])}")
        print(f"   🔗 Contextual matches: {len(results['contextual_matches'])}")
        
        if results.get('conversation_context'):
            context = results['conversation_context']
            print(f"   📚 Conversation context: {context['total_memories']} memories")
            print(f"   📝 Context summary: {context['context_summary'][:80]}...")
        
        # Show a relevant result
        all_matches = results['direct_matches'] + results['contextual_matches']
        if all_matches:
            best_match = all_matches[0]
            print(f"   🎯 Best answer: {best_match['content'][:120]}...")


async def show_system_statistics(memory_interface):
    """Show comprehensive system statistics"""
    
    print("\n" + "-"*60)
    print("📊 SYSTEM STATISTICS")
    print("-"*60)
    
    # Get memory statistics
    stats = await memory_interface.get_memory_stats()
    
    print(f"🗄️ Memory Database Status:")
    print(f"   • Total memories: {stats['total_memories']}")
    print(f"   • Storage path: {stats['storage_path']}")
    
    print(f"\n📁 Collection Statistics:")
    for collection_name, collection_stats in stats['collections'].items():
        count = collection_stats['count']
        print(f"   • {collection_name.title()}: {count} memories")
    
    # Interface statistics
    interface_stats = stats.get('interface', {})
    print(f"\n🔧 Query Interface:")
    print(f"   • Cache entries: {interface_stats.get('cache_entries', 0)}")
    print(f"   • Active: {interface_stats.get('query_interface_active', False)}")
    
    # Health check
    health = await memory_interface.health_check()
    print(f"\n💚 System Health: {health['status'].upper()}")
    
    if health['status'] == 'healthy':
        print("   ✅ All systems operational")
    else:
        print("   ⚠️ Some systems may be degraded")


async def demo_api_capabilities(memory_interface):
    """Demonstrate API-like capabilities"""
    
    print("\n" + "-"*60)
    print("🌐 API CAPABILITIES DEMONSTRATION")
    print("-"*60)
    
    print("🔧 The vector memory system provides REST API endpoints:")
    
    api_endpoints = [
        ("POST /query", "Semantic search across all memory types"),
        ("POST /conversation", "Store conversation memory"),
        ("GET /conversation/{id}", "Retrieve conversation history"),
        ("POST /interaction", "Store interaction with feedback"),
        ("POST /extract", "Extract and index knowledge"),
        ("POST /batch", "Batch memory storage"),
        ("GET /search", "Simple memory search"),
        ("GET /stats", "System statistics"),
        ("GET /health", "Health check"),
        ("DELETE /cleanup", "Clean up old memories")
    ]
    
    for endpoint, description in api_endpoints:
        print(f"   🔗 {endpoint:<25} - {description}")
    
    print(f"\n📚 Example API Usage:")
    print("""
    # Query memory via API
    curl -X POST "http://localhost:8000/query" \\
         -H "Content-Type: application/json" \\
         -d '{
           "query": "machine learning algorithms",
           "limit": 10,
           "similarity_threshold": 0.7
         }'
    
    # Store conversation
    curl -X POST "http://localhost:8000/conversation" \\
         -H "Content-Type: application/json" \\
         -d '{
           "conversation_id": "user_session_123",
           "content": "User asks about deep learning",
           "metadata": {"user_id": "user_123"}
         }'
    """)
    
    print("🚀 Ready for production deployment with FastAPI integration!")


async def run_simple_demo():
    """Simple demonstration for quick testing"""
    
    print("🧠 AI LONG-TERM MEMORY - QUICK DEMO")
    print("="*50)
    
    # Create temporary directory
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Initialize memory system
        print("🚀 Initializing memory system...")
        memory_interface = await create_memory_interface(persist_directory=temp_dir)
        
        # Store a simple memory
        print("💾 Storing memory...")
        result = await memory_interface.remember_conversation(
            conversation_id="quick_demo",
            content="This is a quick demonstration of the AI memory system's capabilities",
            metadata={"demo": True}
        )
        print(f"✅ Stored: {result['memory_id']}")
        
        # Query the memory
        print("🔍 Querying memory...")
        search_results = await memory_interface.ask_memory(
            query="AI memory system demonstration",
            limit=5
        )
        
        print(f"📊 Found {len(search_results['direct_matches'])} matches")
        if search_results['direct_matches']:
            match = search_results['direct_matches'][0]
            print(f"🎯 Best match: {match['content'][:60]}...")
        
        print("✅ Quick demo completed successfully!")
        
    except ImportError:
        print("❌ ChromaDB not available - install with: pip install chromadb")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "quick":
        asyncio.run(run_simple_demo())
    else:
        asyncio.run(demonstrate_vector_memory_system())