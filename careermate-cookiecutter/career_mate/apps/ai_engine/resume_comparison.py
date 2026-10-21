"""
Resume Progress and Version Comparison Module.

Provides deterministic, objective comparison between candidate resume versions:
1. ATS Score progression and point differences (+/- points).
2. Extracted skills comparison (newly detected, retained across versions, no longer detected).
3. Actionable suggestion and improvement tracking (addressed, still relevant, new issues, requiring review).
4. Category breakdown deltas and word count changes.
"""

from django.urls import reverse


def compare_resume_versions(prev_resume, curr_resume):
    """
    Compares two historical resume versions for a candidate.
    Returns structured comparison data for the UI dashboard.
    """
    if not prev_resume or not curr_resume:
        return None

    # 1. ATS Score Comparison
    prev_score = prev_resume.ats_score if prev_resume.ats_score is not None else 0
    curr_score = curr_resume.ats_score if curr_resume.ats_score is not None else 0
    score_diff = curr_score - prev_score

    if score_diff > 0:
        score_direction = "improved"
        score_badge = f"+{score_diff} pts"
    elif score_diff < 0:
        score_direction = "declined"
        score_badge = f"{score_diff} pts"
    else:
        score_direction = "unchanged"
        score_badge = "0 pts"

    # Verify scoring algorithm ruleset consistency
    prev_version_str = prev_resume.scoring_version or "v1.0"
    curr_version_str = curr_resume.scoring_version or "v1.0"
    is_comparable = (prev_version_str == curr_version_str)
    scoring_note = (
        "" if is_comparable
        else f"Scoring methodology updated ({prev_version_str} vs {curr_version_str}). Differences may reflect updated criteria."
    )

    # 2. Skills Comparison
    prev_skills_raw = prev_resume.analysis_data.get("extracted_skills", []) if isinstance(prev_resume.analysis_data, dict) else []
    curr_skills_raw = curr_resume.analysis_data.get("extracted_skills", []) if isinstance(curr_resume.analysis_data, dict) else []

    prev_skills_set = set(prev_skills_raw)
    curr_skills_set = set(curr_skills_raw)

    skills_newly_detected = sorted(list(curr_skills_set - prev_skills_set))
    skills_retained = sorted(list(curr_skills_set & prev_skills_set))
    skills_no_longer_detected = sorted(list(prev_skills_set - curr_skills_set))

    # 3. Suggestions & Improvement Tracking
    prev_suggestions = prev_resume.analysis_data.get("suggestions", []) if isinstance(prev_resume.analysis_data, dict) else []
    curr_suggestions = curr_resume.analysis_data.get("suggestions", []) if isinstance(curr_resume.analysis_data, dict) else []

    curr_suggestion_ids = {s.get("id") for s in curr_suggestions if isinstance(s, dict)}
    prev_suggestion_ids = {s.get("id") for s in prev_suggestions if isinstance(s, dict)}

    addressed_suggestions = []
    relevant_suggestions = []
    potential_improvements = []
    new_issues = []

    for s in prev_suggestions:
        if not isinstance(s, dict):
            continue
        s_id = s.get("id")
        if s_id not in curr_suggestion_ids:
            # Check verifiable criteria
            is_verified = True
            evidence = f"Addressed in Version {curr_resume.version_number}."
            if s_id and s_id.startswith("missing_") and curr_resume.parsed_text:
                section_name = s_id.replace("missing_", "").lower()
                if section_name in curr_resume.parsed_text.lower():
                    evidence = f"Verified: '{section_name.title()}' section detected in Version {curr_resume.version_number}."
                else:
                    is_verified = False
                    evidence = f"Cannot automatically verify resolution of '{s.get('title')}'."

            if is_verified:
                addressed_suggestions.append({
                    "id": s_id,
                    "title": s.get("title"),
                    "description": s.get("description"),
                    "category": s.get("category"),
                    "resolution": f"Addressed in Version {curr_resume.version_number}.",
                    "evidence": evidence,
                    "suggestion": s,
                })
            else:
                potential_improvements.append({
                    "id": s_id,
                    "title": s.get("title"),
                    "description": s.get("description"),
                    "category": s.get("category"),
                    "evidence": evidence,
                    "suggestion": s,
                })
        else:
            relevant_suggestions.append({
                "id": s_id,
                "title": s.get("title"),
                "description": s.get("description"),
                "category": s.get("category"),
                "impact": s.get("impact", ""),
                "evidence": f"Still relevant in Version {curr_resume.version_number}.",
                "suggestion": s,
            })

    for s in curr_suggestions:
        if not isinstance(s, dict):
            continue
        s_id = s.get("id")
        if s_id not in prev_suggestion_ids:
            new_issues.append({
                "id": s_id,
                "title": s.get("title"),
                "description": s.get("description"),
                "category": s.get("category"),
                "impact": s.get("impact", ""),
                "evidence": f"Newly flagged in Version {curr_resume.version_number}.",
                "suggestion": s,
            })

    # 4. Category Breakdown Deltas
    prev_breakdown_list = prev_resume.analysis_data.get("breakdown", []) if isinstance(prev_resume.analysis_data, dict) else []
    curr_breakdown_list = curr_resume.analysis_data.get("breakdown", []) if isinstance(curr_resume.analysis_data, dict) else []

    prev_b_map = {b.get("category"): b.get("score", 0) for b in prev_breakdown_list if isinstance(b, dict)}
    category_deltas = []
    breakdown_comparison = []
    for b in curr_breakdown_list:
        if isinstance(b, dict):
            cat = b.get("category")
            c_score = b.get("score", 0)
            p_score = prev_b_map.get(cat, 0)
            diff = c_score - p_score
            delta_dict = {
                "category": cat,
                "prev_score": p_score,
                "curr_score": c_score,
                "max": b.get("max", 0),
                "diff": diff,
                "delta": diff,
                "message": b.get("message", ""),
            }
            category_deltas.append(delta_dict)
            breakdown_comparison.append(delta_dict)

    # 5. Word Count and Readability
    prev_words = prev_resume.analysis_data.get("word_count", 0) if isinstance(prev_resume.analysis_data, dict) else 0
    curr_words = curr_resume.analysis_data.get("word_count", 0) if isinstance(curr_resume.analysis_data, dict) else 0
    if not prev_words and prev_resume.parsed_text:
        prev_words = len(prev_resume.parsed_text.split())
    if not curr_words and curr_resume.parsed_text:
        curr_words = len(curr_resume.parsed_text.split())
    word_diff = curr_words - prev_words

    if score_diff > 0:
        trend = "improvement"
        summary = f"ATS score increased by {score_diff} points from Version {prev_resume.version_number} ({prev_score}) to Version {curr_resume.version_number} ({curr_score})."
    elif score_diff < 0:
        trend = "decline"
        summary = f"ATS score decreased by {abs(score_diff)} points from Version {prev_resume.version_number} ({prev_score}) to Version {curr_resume.version_number} ({curr_score})."
    else:
        trend = "unchanged"
        summary = f"ATS score remained consistent at {curr_score} between Version {prev_resume.version_number} and Version {curr_resume.version_number}."

    skills_data = {
        "added": skills_newly_detected,
        "retained": skills_retained,
        "dropped": skills_no_longer_detected,
        "added_count": len(skills_newly_detected),
        "retained_count": len(skills_retained),
        "dropped_count": len(skills_no_longer_detected),
        "prev_count": len(prev_skills_set),
        "curr_count": len(curr_skills_set),
    }

    suggestions_data = {
        "addressed": addressed_suggestions,
        "still_relevant": relevant_suggestions,
        "new_issues": new_issues,
        "requiring_review": potential_improvements,
    }

    return {
        "prev_resume": prev_resume,
        "curr_resume": curr_resume,
        "previous_resume": prev_resume,
        "current_resume": curr_resume,
        "prev_version": prev_resume.version_number,
        "curr_version": curr_resume.version_number,
        "prev_score": prev_score,
        "curr_score": curr_score,
        "previous_score": prev_score,
        "current_score": curr_score,
        "score_diff": score_diff,
        "point_difference": score_diff,
        "difference_display": score_badge,
        "score_direction": score_direction,
        "score_badge": score_badge,
        "trend": trend,
        "summary": summary,
        "is_comparable": is_comparable,
        "scoring_version": curr_version_str,
        "scoring_note": scoring_note,
        "skills": skills_data,
        "suggestions": suggestions_data,
        "skills_newly_detected": skills_newly_detected,
        "skills_retained": skills_retained,
        "skills_no_longer_detected": skills_no_longer_detected,
        "skills_prev_count": len(prev_skills_set),
        "skills_curr_count": len(curr_skills_set),
        "addressed_suggestions": addressed_suggestions,
        "relevant_suggestions": relevant_suggestions,
        "new_issues": new_issues,
        "potential_improvements": potential_improvements,
        "category_deltas": category_deltas,
        "breakdown_comparison": breakdown_comparison,
        "prev_words": prev_words,
        "curr_words": curr_words,
        "prev_word_count": prev_words,
        "curr_word_count": curr_words,
        "word_diff": word_diff,
        "word_count_delta": word_diff,
    }


def get_candidate_version_history(candidate):
    """
    Compiles complete historical version timeline for a candidate.
    Calculates sequential score differences across chronological uploads.
    """
    resumes_chronological = list(candidate.resumes.order_by("version_number", "uploaded_at"))
    if not resumes_chronological:
        return []

    history = []
    prev_score = None

    for r in resumes_chronological:
        score = r.ats_score
        diff = (score - prev_score) if (score is not None and prev_score is not None) else None
        
        diff_badge = None
        if diff is not None:
            if diff > 0:
                diff_badge = f"+{diff}"
            elif diff < 0:
                diff_badge = str(diff)
            else:
                diff_badge = "0"

        history.append({
            "resume": r,
            "version_number": r.version_number,
            "file_name": r.file_name,
            "uploaded_at": r.uploaded_at,
            "status": r.status,
            "ats_score": score,
            "score_diff": diff,
            "diff_badge": diff_badge,
            "has_file": r.file_exists,
            "word_count": r.analysis_data.get("word_count") if isinstance(r.analysis_data, dict) else None,
            "skill_count": len(r.analysis_data.get("extracted_skills", [])) if isinstance(r.analysis_data, dict) else 0,
            "suggestions_count": len(r.analysis_data.get("suggestions", [])) if isinstance(r.analysis_data, dict) else 0,
        })

        if score is not None:
            prev_score = score

    return history
