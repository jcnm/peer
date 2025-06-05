#!/usr/bin/env python3
"""
Benchmark script to test WhisperX model performance
Tests initialization time and memory usage for different model sizes
"""

import time
import psutil
import os
import whisperx
import gc

def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def benchmark_model(model_name):
    """Benchmark a specific WhisperX model"""
    print(f"\n🔄 Testing {model_name.upper()} model...")
    
    # Memory before loading
    mem_before = get_memory_usage()
    
    # Time the model loading
    start_time = time.time()
    try:
        model = whisperx.load_model(
            model_name,
            device='cpu',
            compute_type='float32',
            language='fr'  # Specify French to avoid detection overhead
        )
        load_time = time.time() - start_time
        
        # Memory after loading
        mem_after = get_memory_usage()
        mem_used = mem_after - mem_before
        
        print(f"✅ {model_name.upper()}:")
        print(f"   📊 Temps de chargement: {load_time:.2f}s")
        print(f"   💾 Mémoire utilisée: {mem_used:.1f} MB")
        print(f"   📈 Mémoire totale: {mem_after:.1f} MB")
        
        # Clean up
        del model
        gc.collect()
        
        return {
            'model': model_name,
            'load_time': load_time,
            'memory_used': mem_used,
            'success': True
        }
        
    except Exception as e:
        print(f"❌ {model_name.upper()} FAILED: {str(e)[:100]}")
        return {
            'model': model_name,
            'load_time': 0,
            'memory_used': 0,
            'success': False,
            'error': str(e)
        }

def main():
    print("🎙️ BENCHMARK WHISPERX MODELS")
    print("=" * 50)
    
    models = ['tiny', 'small', 'medium', 'large-v3']
    results = []
    
    initial_memory = get_memory_usage()
    print(f"💾 Mémoire initiale: {initial_memory:.1f} MB")
    
    for model_name in models:
        result = benchmark_model(model_name)
        results.append(result)
        
        # Wait a bit between tests
        time.sleep(2)
    
    # Summary
    print("\n📋 RÉSUMÉ DES PERFORMANCES")
    print("=" * 50)
    
    successful_results = [r for r in results if r['success']]
    
    if successful_results:
        print("Modèle    | Temps (s) | Mémoire (MB) | Recommandation")
        print("-" * 55)
        
        for result in successful_results:
            model = result['model'].upper().ljust(8)
            load_time = f"{result['load_time']:.1f}s".ljust(9)
            memory = f"{result['memory_used']:.0f} MB".ljust(12)
            
            # Recommendation based on performance
            if result['model'] == 'tiny':
                rec = "🏃‍♂️ Vitesse max"
            elif result['model'] == 'small':
                rec = "🚀 Équilibré"
            elif result['model'] == 'medium':
                rec = "🎯 Précision++"
            else:
                rec = "🏆 Max qualité"
            
            print(f"{model} | {load_time} | {memory} | {rec}")
    
    print("\n💡 CONSEILS D'UTILISATION:")
    print("• TINY: Tests rapides, démonstrations")
    print("• SMALL: Usage quotidien recommandé")
    print("• MEDIUM: Dictée importante, transcription")
    print("• LARGE-V3: Qualité professionnelle maximum")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Benchmark interrompu par l'utilisateur")
    except Exception as e:
        print(f"\n❌ Erreur pendant le benchmark: {e}")
