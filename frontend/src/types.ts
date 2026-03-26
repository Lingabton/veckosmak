/** Core types matching backend Pydantic models */

export interface Nutrition {
  calories: number | null
  protein: number | null
  carbohydrates: number | null
  fat: number | null
}

export interface Ingredient {
  name: string
  amount: number
  unit: string
  category: string
  is_pantry_staple: boolean
}

export interface Recipe {
  id: string
  title: string
  source_url: string | null
  source: string
  servings: number
  cook_time_minutes: number
  difficulty: 'easy' | 'medium' | 'hard'
  tags: string[]
  diet_labels: string[]
  ingredients: Ingredient[]
  instructions: string[]
  image_url: string | null
  rating: number | null
  rating_count: number | null
  nutrition: Nutrition | null
  cooking_method: string | null
}

export interface Offer {
  id: string
  store_id: string
  product_name: string
  brand: string | null
  category: string
  offer_price: number
  original_price: number | null
  unit: string
  quantity_deal: string | null
  max_per_household: number | null
  valid_from: string
  valid_to: string
  requires_membership: boolean
  image_url: string | null
  raw_text: string
}

export interface PlannedMeal {
  day: string
  recipe: Recipe
  scaled_servings: number
  offer_matches: Offer[]
  estimated_cost: number
  estimated_cost_without_offers: number
  reasoning: string
  popularity_score: number
  is_fallback: boolean
  mealprep_tip: string
}

export interface ShoppingItem {
  ingredient_name: string
  total_amount: number
  unit: string
  category: string
  matched_offer: Offer | null
  estimated_price: number
  is_on_offer: boolean
  used_in: string[]
}

export interface ShoppingList {
  items: ShoppingItem[]
  total_estimated_cost: number
  items_on_offer: number
  items_not_on_offer: number
}

export interface TimeMix {
  quick_count: number
  medium_count: number
  slow_count: number
}

export interface UserPreferences {
  household_size: number
  num_dinners: number
  budget_per_week: number | null
  max_cook_time: number | null
  time_mix: TimeMix | null
  dietary_restrictions: string[]
  lifestyle_preferences: string[]
  disliked_ingredients: string[]
  pinned_offer_ids: string[]
  store_id: string
  has_children: boolean
  selected_days: string[]
}

export interface WeeklyMenu {
  id: string
  week_number: number
  year: number
  store_id: string
  preferences: UserPreferences
  meals: PlannedMeal[]
  shopping_list: ShoppingList
  total_cost: number
  total_cost_without_offers: number
  total_savings: number
  savings_percentage: number
  generated_at: string
  pinned_offers: Offer[]
  budget_exceeded: boolean
  budget_exceeded_by: number
  confirmed_savings: number
  estimated_savings: number
  date_range: string
  active_filters: string[]
}

export interface BonusOffer extends Offer {
  discount: number
}
