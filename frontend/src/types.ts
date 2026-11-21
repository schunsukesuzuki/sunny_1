/** v0.13 API data schemas are versioned in backend/app/main.py.
 * The UI uses expandable audit JSON to preserve future versioned diagnostic fields.
 */
export interface Claim {case_id:string;arrival_order:number;required_skill:string;duration_hours:number;deadline_day:number;amount_eur:number;business_priority:number}
export interface Reviewer {reviewer_id:string;skills:string[];daily_capacity_hours:number[]}
export interface Schedule {assignments:{case_id:string;reviewer_id:string;day:number;hours:number}[];unassigned_case_ids:string[]}
