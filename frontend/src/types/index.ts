export interface Restaurant {
  id: number;
  name: string;
  city?: string;
  location?: string;
  website?: string;
  category?: string;
  created_at?: string;
  is_new?: boolean;
}

export interface RestaurantSuggestion {
  name: string;
  city?: string;
  source: string;
}

export interface AnalysisRun {
  id: number;
  restaurant_id: number;
  period_start?: string;
  period_end?: string;
  status: string;
  created_at?: string;
  completed_at?: string;
  data_quality_score?: number;
  notes?: string;
  datasets?: {
    menu: boolean;
    sales: boolean;
    reviews: boolean;
    costs: boolean;
  };
}

export interface DataQualityReport {
  file_type: string;
  total_records: number;
  accepted_records: number;
  rejected_records: number;
  duplicate_records: number;
  missing_values: Record<string, number>;
  invalid_records: number;
  unmatched_items: string[];
  warnings: string[];
  errors: string[];
  quality_score: number;
}

export interface ValidationResult {
  is_valid: boolean;
  errors: string[];
  warnings: string[];
}

export interface DatasetPreview {
  file_type: string;
  columns: string[];
  total_rows: number;
  rows: Record<string, any>[];
}

export interface ItemSalesMetrics {
  item_id?: string;
  item_name: string;
  category?: string;
  total_quantity: number;
  total_revenue: number;
  avg_price?: number;
  sales_rank?: number;
  revenue_contribution_pct?: number;
  period_trend?: string; // growing | declining | stable | no_data | new
  data_points: number;
}

export interface SalesAnalysisSummary {
  total_revenue: number;
  total_units: number;
  item_count: number;
  period_start?: string;
  period_end?: string;
  top_items: ItemSalesMetrics[];
  weak_items: ItemSalesMetrics[];
  category_summary: Record<string, { revenue: number; quantity: number; item_count: number }>;
  warnings: string[];
}

export interface RevenueTrendPoint {
  date: string;
  revenue: number;
  rolling_7d?: number;
}

export interface CategoryShare {
  category: string;
  revenue: number;
  units: number;
  percentage: number;
}

export interface AnalyticsSummaryOut {
  summary: SalesAnalysisSummary;
  daily_trends: RevenueTrendPoint[];
  category_shares: CategoryShare[];
}

export interface ProfitabilityMetrics {
  item_id?: string;
  item_name: string;
  selling_price?: number;
  ingredient_cost?: number;
  packaging_cost?: number;
  total_cost?: number;
  contribution_margin?: number;
  margin_pct?: number;
  calculable: boolean;
  limitation_note?: string;
}

export interface ReviewTheme {
  theme: string;
  sentiment: string;
  frequency: number;
  representative_quote?: string;
}

export interface SentimentSummary {
  item_name?: string;
  positive_pct: number;
  negative_pct: number;
  neutral_pct: number;
  review_count: number;
  avg_rating?: number;
  verified_count: number;
  snippet_count: number;
  verified_avg_rating?: number;
  snippet_avg_rating?: number;
  rating_distribution: Record<string, number>;
  complaints: { theme: string; frequency: number; representative_quote?: string }[];
  appreciated_features: { theme: string; frequency: number; representative_quote?: string }[];
  themes: ReviewTheme[];
  source_coverage: string[];
  limitations: string[];
}

export interface ItemReviewInsight {
  item_name: string;
  mention_count: number;
  verified_count: number;
  snippet_count: number;
  avg_rating?: number;
  positive_pct: number;
  negative_pct: number;
  neutral_pct: number;
  top_complaint?: string;
  top_compliment?: string;
  sample_reviews: Record<string, any>[];
}

export interface ReviewTrendRecord {
  period: string;
  total_reviews: number;
  avg_rating?: number;
  positive_pct: number;
  negative_pct: number;
  neutral_pct: number;
  verified_count: number;
  snippet_count: number;
}

export interface Approval {
  id: number;
  recommendation_id: number;
  decision: 'approved' | 'rejected' | 'saved_for_later';
  decided_by: string;
  notes?: string;
  decided_at: string;
}

export interface Recommendation {
  id: number;
  run_id: number;
  item_id?: string;
  item_name: string;
  action: 'IMPROVE' | 'REMOVE' | 'PROMOTE' | 'REPRICE' | 'INSUFFICIENT_EVIDENCE';
  priority?: 'high' | 'medium' | 'low';
  confidence_score?: number;
  reasoning?: string;
  alternative_actions: string[];
  expected_benefits?: string;
  potential_risks?: string;
  missing_information?: string;
  next_steps: string[];
  sales_metrics?: Record<string, any>;
  review_themes?: Record<string, any>;
  profitability?: Record<string, any>;
  requires_approval: boolean;
  success_metrics?: string;
  created_at?: string;
  approval?: Approval;
}

export interface Experiment {
  id: number;
  run_id: number;
  recommendation_id?: number;
  title: string;
  hypothesis?: string;
  intervention?: string;
  baseline_start?: string;
  baseline_end?: string;
  test_start?: string;
  test_end?: string;
  success_criteria?: string;
  guardrail_metrics?: string;
  status: 'proposed' | 'approved' | 'active' | 'completed' | 'cancelled';
  created_at?: string;
  approved_at?: string;
  results?: {
    id: number;
    experiment_id: number;
    metric_name: string;
    baseline_value?: number;
    test_value?: number;
    change_pct?: number;
    notes?: string;
  }[];
}

export interface WasteRecord {
  id?: number;
  run_id?: number;
  ingredient_name: string;
  quantity: number;
  unit: string;
  unit_cost: number;
  waste_reason?: string;
  associated_dish?: string;
  image_item_name?: string;
  image_confidence?: number;
  verified_by_user?: boolean;
  created_at?: string;
}

export interface WasteIntelligenceSummary {
  measured: {
    total_waste_cost: number;
    calculable_records: number;
    uncalculable_records: number;
    by_ingredient: Record<string, number>;
    limitations: string[];
  };
  spoilage: {
    slow_moving_items: {
      item_name: string;
      units_sold: number;
      daily_velocity: number;
      unit_cost: number;
      weekly_exposure: number;
      risk_level: 'High' | 'Medium' | 'Low';
      suggested_action: string;
    }[];
    median_velocity: number;
    total_weekly_exposure: number;
    high_risk_count: number;
    action_items: string[];
    limitations: string[];
  };
  records: WasteRecord[];
}
