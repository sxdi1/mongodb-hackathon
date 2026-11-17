export type MemberId = "alex" | "sarah" | "omar" | "maya";
export type SplitMode = "equal" | "itemized";
export type Payment = "unpaid" | "sent" | "settled";
export type ActivityId = "escape" | "golf";
export type RestaurantId = "garden" | "mezze";
export const members: { id: MemberId; name: string; initials: string; color: string; preference: string }[] = [
  { id: "alex", name: "Alex", initials: "AL", color: "peach", preference: "Up for an adventure · driving" },
  { id: "sarah", name: "Sarah", initials: "SK", color: "pink", preference: "Vegetarian · escape rooms" },
  { id: "omar", name: "Omar", initials: "OH", color: "blue", preference: "Halal food · flexible on plans" },
  { id: "maya", name: "Maya", initials: "MC", color: "mint", preference: "Public transit · budget conscious" },
];
export const activities = [
  { id: "escape" as const, name: "The Great Escape", category: "ESCAPE ROOM", location: "Downtown Toronto", duration: "60 min", price: 3200, tag: "Best fit for your crew", image: "escape", description: "Four friends. One mystery. Find your way out together." },
  { id: "golf" as const, name: "Par-Tee Putt", category: "INDOOR MINI GOLF", location: "Entertainment District", duration: "90 min", price: 2900, tag: "A little friendly competition", image: "golf", description: "A playful round of mini golf, with a downtown twist." },
];
export const restaurants = [
  { id: "garden" as const, name: "The Garden Table", location: "Queen Street West", price: 2700, description: "Seasonal bowls, cozy corners, and something for everyone.", tag: "Halal options · Vegetarian friendly" },
  { id: "mezze" as const, name: "Mezze & Co.", location: "King Street West", price: 2500, description: "Bright Mediterranean plates made for sharing.", tag: "Halal options · Vegetarian friendly" },
];
export const stages = ["Your weekend starts here", "The group has an idea", "A few things you’ll love", "Activity booked, together", "A dinner suggestion", "Everyone gets a seat", "Dinner is on the itinerary", "A receipt joins the chat", "The math, taken care of", "One last confirmation", "A great day, all settled"];
export const sampleItems = [
  { id: "bowl", name: "Roasted vegetable bowl", cents: 2200, owner: "sarah" as MemberId },
  { id: "chicken", name: "Halal chicken plate", cents: 2400, owner: "omar" as MemberId },
  { id: "pasta", name: "Wild mushroom pasta", cents: 2600, owner: "alex" as MemberId },
  { id: "falafel", name: "Falafel & hummus", cents: 2000, owner: "maya" as MemberId },
  { id: "drinks", name: "Four house lemonades", cents: 1200, owner: "all" as const },
];
export type ReceiptItem = { id: string; name: string; cents: number; owner: MemberId | "all" };
export const money = (cents: number) => new Intl.NumberFormat("en-CA", { style: "currency", currency: "CAD" }).format(cents / 100);
// Allocate remainder cents in a stable order. Never round each share independently.
export function allocate(total: number, weights: number[]): number[] {
  const sum = weights.reduce((a, b) => a + b, 0);
  if (!sum) return weights.map((_, i) => Math.floor(total / weights.length) + (i < total % weights.length ? 1 : 0));
  const shares = weights.map(w => Math.floor(total * w / sum));
  const order = weights.map((w, i) => ({ i, fraction: total * w / sum - shares[i] })).sort((a, b) => b.fraction - a.fraction || a.i - b.i);
  const remainder = total - shares.reduce((a, b) => a + b, 0);
  for (let i = 0; i < remainder; i++) shares[order[i].i]++;
  return shares;
}
export function calculateReceipt(items: ReceiptItem[], mode: SplitMode) {
  const subtotal = items.reduce((sum, item) => sum + item.cents, 0);
  const tax = Math.round(subtotal * 0.13);
  const tip = Math.round(subtotal * 0.15);
  const total = subtotal + tax + tip;
  const bases = [0, 0, 0, 0];
  for (const item of items) {
    if (item.owner === "all") allocate(item.cents, [1, 1, 1, 1]).forEach((v, i) => bases[i] += v);
    else bases[members.findIndex(m => m.id === item.owner)] += item.cents;
  }
  const shares = allocate(total, mode === "equal" ? [1, 1, 1, 1] : bases);
  return { subtotal, tax, tip, total, shares };
}
export type DemoState = {
  step: number; activity: ActivityId; restaurant: RestaurantId; votes: MemberId[];
  mode: SplitMode; items: ReceiptItem[]; payments: Record<MemberId, Payment>;
};
export function snapshot(step: number, activity: ActivityId = "escape", restaurant: RestaurantId = "garden"): DemoState {
  return { step, activity, restaurant, votes: step >= 3 ? members.map(m => m.id) : [], mode: "equal", items: sampleItems.map(i => ({ ...i })),
    payments: { alex: "settled", sarah: step >= 10 ? "settled" : step >= 9 ? "sent" : "unpaid", omar: step >= 10 ? "settled" : step >= 9 ? "sent" : "unpaid", maya: step >= 10 ? "settled" : step >= 9 ? "sent" : "unpaid" } };
}
export type DemoAction =
  | { type: "goto"; step: number }
  | { type: "reset" }
  | { type: "activity"; id: ActivityId }
  | { type: "vote"; id: MemberId }
  | { type: "book" }
  | { type: "restaurant"; id: RestaurantId }
  | { type: "mode"; mode: SplitMode }
  | { type: "item"; id: string; cents?: number; owner?: MemberId | "all" }
  | { type: "payment"; id: MemberId; kind: "sent" | "received" };
export function demoReducer(state: DemoState, action: DemoAction): DemoState {
  switch (action.type) {
    case "goto": {
      const step = Math.max(0, Math.min(10, action.step));
      if (step < state.step) return snapshot(step, state.activity, state.restaurant);
      const next = { ...state, step };
      if (step >= 3) next.votes = members.map(m => m.id);
      if (step >= 10) next.payments = { alex: "settled", sarah: "settled", omar: "settled", maya: "settled" };
      else if (step >= 9) next.payments = Object.fromEntries(Object.entries(state.payments).map(([id, status]) => [id, status === "unpaid" ? "sent" : status])) as Record<MemberId, Payment>;
      return next;
    }
    case "reset": return snapshot(0);
    case "activity": return { ...state, activity: action.id, votes: [] };
    case "vote": return { ...state, votes: state.votes.includes(action.id) ? state.votes.filter(id => id !== action.id) : [...state.votes, action.id] };
    case "book": return state.votes.length === 4 ? { ...state, step: Math.max(3, state.step) } : state;
    case "restaurant": return { ...state, restaurant: action.id, step: Math.max(6, state.step) };
    case "mode": return state.mode === action.mode ? state : { ...state, mode: action.mode, payments: snapshot(0).payments, step: 8 };
    case "item": return { ...state, step: 8, items: state.items.map(i => i.id === action.id ? { ...i, ...(action.cents === undefined ? {} : { cents: action.cents }), ...(action.owner === undefined ? {} : { owner: action.owner }) } : i), payments: snapshot(0).payments };
    case "payment": {
      if (action.id === "alex") return state;
      const current = state.payments[action.id];
      const status = action.kind === "sent" && current === "unpaid" ? "sent" : action.kind === "received" && current === "sent" ? "settled" : current;
      const payments = { ...state.payments, [action.id]: status };
      return { ...state, payments, step: Object.values(payments).every(p => p === "settled") ? 10 : state.step };
    }
  }
}
