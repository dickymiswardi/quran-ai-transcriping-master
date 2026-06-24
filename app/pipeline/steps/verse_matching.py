"""
Verse Matching Step - Step 7 of the pipeline.

Matches transcribed text to Quran verses using boundary detection.
"""

from app.pipeline.base import PipelineStep, PipelineContext
import quran_ayah_lookup as qal
from rapidfuzz import fuzz

class VerseMatchingStep(PipelineStep):
    def __init__(self):
        super().__init__()
    
    def validate_input(self, context: PipelineContext) -> bool:
        if not context.final_transcription:
            self.logger.error("No final transcription in context")
            return False
        return True
    
    def process(self, context: PipelineContext) -> PipelineContext:
        ctn = context.combined_transcription_normalized
        self.logger.info(f"Matching verses for transcription ({len(ctn)} chars)...")
        
        bounds = getattr(context, 'config', {}).get('manual_bounds')
        
        if bounds:
            self.logger.info(f"Using manual bounds: {bounds}")
            verses_in_range = []
            
            # Dapatkan seluruh ayat dalam database QAL
            all_verses = []
            for s in range(1, 115):
                a = 1
                while True:
                    try:
                        v = qal.get_verse(s, a)
                        if v:
                            all_verses.append(v)
                            a += 1
                        else:
                            break
                    except:
                        break
                        
            start_s = bounds['start_surah']
            start_a = bounds['start_ayah']
            end_s = bounds['end_surah']
            end_a = bounds['end_ayah']
            
            for v in all_verses:
                v_pos = (v.surah_number, v.ayah_number)
                if (start_s, start_a) <= v_pos <= (end_s, end_a):
                    verses_in_range.append({
                        'text_normalized': v.text_normalized,
                        'surah_number': v.surah_number,
                        'ayah_number': v.ayah_number,
                        'text': v.text,
                        'is_basmalah': v.is_basmalah,
                        'word_count': len(v.text_normalized.split())
                    })
                    
        else:
            # AUTO DETECTION
            results = qal.search_sliding_window(ctn)
            
            if not results:
                self.logger.warning("No verse matches found")
                context.matched_verses = []
                context.match_similarity = 0.0
                context.match_boundaries = {}
                return context
            
            best_match = max(results, key=lambda r: r.similarity)
            sorted_best_match = sorted(best_match.verses, key=lambda v: (v.surah_number, v.ayah_number))
            
            if ctn.startswith("بسم الله الرحمن الرحيم"):
                basmalah_index = None
                for i, verse in enumerate(sorted_best_match):
                    if verse.is_basmalah:
                        basmalah_index = i
                        break
                if basmalah_index is not None:
                    sorted_best_match = sorted_best_match[basmalah_index:]
            
            best_match.verses = sorted_best_match
            
            matched_ayahs = []
            for verse in best_match.verses:
                matched_ayahs.append({
                    'surah_number': verse.surah_number,
                    'ayah_number': verse.ayah_number,
                    'text': verse.text,
                    'text_normalized': verse.text_normalized,
                    'is_basmalah': verse.is_basmalah
                })
                
            match_boundaries = {
                'start_surah': best_match.start_surah,
                'start_ayah': best_match.start_ayah,
                'start_word': best_match.start_word,
                'end_surah': best_match.end_surah,
                'end_ayah': best_match.end_ayah,
                'end_word': best_match.end_word
            }
            
            context.matched_verses = best_match.verses
            context.matched_ayahs = matched_ayahs
            context.match_similarity = best_match.similarity
            context.match_boundaries = match_boundaries
            context.matched_text = best_match.matched_text
            context.query_text = best_match.query_text
            
            verses_in_range = []
            for verse in best_match.verses:
                verse_position = (verse.surah_number, verse.ayah_number)
                start_position = (match_boundaries['start_surah'], match_boundaries['start_ayah'])
                end_position = (match_boundaries['end_surah'], match_boundaries['end_ayah'])
                
                if start_position <= verse_position <= end_position:
                    verses_in_range.append({
                        'text_normalized': verse.text_normalized,
                        'surah_number': verse.surah_number,
                        'ayah_number': verse.ayah_number,
                        'text': verse.text,
                        'is_basmalah': verse.is_basmalah,
                        'word_count': len(verse.text_normalized.split())
                    })
        
        # BOUNDARY DETECTION ALGORITHM (START WORD -> END WORD)
        cleaned_transcriptions = context.cleaned_transcriptions
        combined_words = []
        for chunk in cleaned_transcriptions:
            words = chunk.get('normalized_text', '').split()
            for word in words:
                combined_words.append({
                    'word': word,
                    'start_time': chunk.get('start_time'),
                    'end_time': chunk.get('end_time'),
                    'chunk': chunk
                })
                
        search_idx = 0
        matched_chunk_verses = []
        
        for verse in verses_in_range:
            verse_key = f"Surah {verse['surah_number']}:Ayah {verse['ayah_number']}"
            v_words = verse['text_normalized'].split()
            if not v_words:
                continue
                
            start_word = v_words[0]
            end_word = v_words[-1]
            
            # Find FIRST occurrence of the start word
            best_start_idx = search_idx
            best_start_score = 0
            for i in range(search_idx, min(len(combined_words), search_idx + 25)):
                score = fuzz.ratio(combined_words[i]['word'], start_word)
                if score > best_start_score:
                    best_start_score = score
                    best_start_idx = i
                if score > 85: break
                
            # Find LAST occurrence of the end word
            lookahead = min(len(combined_words), best_start_idx + len(v_words) + 25)
            best_end_idx = best_start_idx
            best_end_score = 0
            for i in range(lookahead - 1, best_start_idx - 1, -1):
                score = fuzz.ratio(combined_words[i]['word'], end_word)
                if score > best_end_score:
                    best_end_score = score
                    best_end_idx = i
                if score > 85: break
                
            if best_start_idx >= len(combined_words) or best_end_idx >= len(combined_words):
                self.logger.warning(f"Kata tidak cukup untuk memetakan {verse_key}. Menghentikan pencarian batas ayat.")
                break

            start_time = combined_words[best_start_idx]['start_time']
            end_time = combined_words[best_end_idx]['end_time']
            
            verse_entry = {
                'surah_number': verse['surah_number'],
                'ayah_number': verse['ayah_number'],
                'text': verse['text'],
                'text_normalized': verse['text_normalized'],
                'is_basmalah': verse['is_basmalah'],
                'start_time': start_time,
                'end_time': end_time,
                'chunks': [] # No small chunks
            }
            matched_chunk_verses.append(verse_entry)
            
            self.logger.info(f"{verse_key} boundaries: {start_time}s to {end_time}s")
            search_idx = best_end_idx + 1
            
        # Bypass downstream steps by filling verse_details directly
        context.verse_details = matched_chunk_verses
        
        return context
