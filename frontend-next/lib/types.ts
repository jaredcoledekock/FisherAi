export type SpeciesPlan = {
  species: string;
  label: string;
  score: number;
  legal?: string;
};

export type PlanWindow = {
  date: string;
  window: string;
  window_id: string;
  score: number;
  per_species: SpeciesPlan[];
  wind_speed: number;
  wind_deg: number;
  swell_height: number;
  swell_period: number;
  sea_temp: number;
  tide_phase: string;
  day_windows?: {
    window_id: string;
    window: string;
    wind_speed: number;
    swell_height: number;
    sea_temp: number;
    tide_phase: string;
  }[];
  sources?: {
    wind?: string | null;
    wind_deg?: string | null;
    swell?: string | null;
    swell_period?: string | null;
    sea_temp?: string | null;
    tide?: string | null;
  };
  explanation?: string;
  factors?: string[];
};

export type Area = {
  id: string;
  name: string;
  lat: number;
  lon: number;
  coast_facing: string;
  notes?: string;
  legal?: string;
};

export type Region = {
  id: string;
  name: string;
  areas: Area[];
};

export type MetaResponse = {
  regions: Region[];
  species: string[];
  defaults?: {
    region_id: string;
    area_id: string;
  };
};

export type PlanRequest = {
  region_id: string;
  area_id: string;
  species: string[];
  start_date: string;
  end_date: string;
};

export type PlanResponse = {
  region: Region;
  area: Area;
  species: string[];
  generated_at: string;
  results: PlanWindow[];
  sources: string[];
};

export type Preset = PlanRequest;
