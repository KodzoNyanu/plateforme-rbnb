-- =============================================================================
--  PLATEFORME DE LOCATIONS IMMOBILIÈRES — TOGO
--  Schéma PostgreSQL complet + données de départ
--  Cible : PostgreSQL 13+  (aucune extension requise)
--
--  La position géographique est stockée en latitude/longitude (DOUBLE PRECISION).
--  → Suffisant pour afficher des marqueurs sur une carte.
--  → Pour du spatial avancé (rayon, polygones), on ajoutera PostGIS plus tard.
--
--  Exécution recommandée :  python db/init_db.py
--  (ou manuellement : psql -d rbnb_togo -f db/schema.sql)
-- =============================================================================

-- ── TYPES ÉNUMÉRÉS ───────────────────────────────────────────────────────────
DO $$ BEGIN CREATE TYPE user_role          AS ENUM ('locataire','proprietaire','agence','admin');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE mode_location      AS ENUM ('longue_duree','courte_duree','les_deux');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE statut_annonce     AS ENUM ('brouillon','en_validation','publiee','loue','archivee');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE unite_tarif        AS ENUM ('mois','nuit','semaine');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE type_valeur        AS ENUM ('score','numerique','booleen','texte');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE statut_reservation AS ENUM ('en_attente_paiement','confirmee','annulee','terminee');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE methode_paiement   AS ENUM ('paypal','mobile_money','carte','sur_place','cinetpay');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
-- Ajout rétro-compatible si le type existait déjà sans 'cinetpay'
ALTER TYPE methode_paiement ADD VALUE IF NOT EXISTS 'cinetpay';
DO $$ BEGIN CREATE TYPE type_paiement      AS ENUM ('frais_reservation','acompte','solde','loyer');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE statut_paiement    AS ENUM ('initie','paye','echoue','rembourse');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE statut_commission  AS ENUM ('due','percue','reversee_bailleur');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- =============================================================================
--  DOMAINE 1 — GÉOGRAPHIE  (Région > Ville > Commune > Quartier)
-- =============================================================================
CREATE TABLE IF NOT EXISTS regions (
    id          SERIAL PRIMARY KEY,
    nom         VARCHAR(120) NOT NULL UNIQUE,
    slug        VARCHAR(140) NOT NULL UNIQUE,
    chef_lieu   VARCHAR(120),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS villes (
    id          SERIAL PRIMARY KEY,
    region_id   INT NOT NULL REFERENCES regions(id) ON DELETE RESTRICT,
    nom         VARCHAR(120) NOT NULL,
    slug        VARCHAR(140) NOT NULL,
    UNIQUE (region_id, nom)
);

CREATE TABLE IF NOT EXISTS communes (
    id          SERIAL PRIMARY KEY,
    ville_id    INT NOT NULL REFERENCES villes(id) ON DELETE RESTRICT,
    nom         VARCHAR(120) NOT NULL,
    slug        VARCHAR(140) NOT NULL,
    UNIQUE (ville_id, nom)
);

CREATE TABLE IF NOT EXISTS quartiers (
    id          SERIAL PRIMARY KEY,
    commune_id  INT NOT NULL REFERENCES communes(id) ON DELETE RESTRICT,
    nom         VARCHAR(120) NOT NULL,
    slug        VARCHAR(140) NOT NULL,
    latitude    DOUBLE PRECISION,
    longitude   DOUBLE PRECISION,
    description TEXT,
    UNIQUE (commune_id, nom)
);
CREATE INDEX IF NOT EXISTS idx_quartiers_commune ON quartiers (commune_id);

-- =============================================================================
--  DOMAINE 2 — UTILISATEURS
-- =============================================================================
CREATE TABLE IF NOT EXISTS users (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email         VARCHAR(180) UNIQUE,
    telephone     VARCHAR(20)  UNIQUE,
    password_hash VARCHAR(255),
    nom_complet   VARCHAR(160) NOT NULL,
    role          user_role NOT NULL DEFAULT 'locataire',
    is_verified   BOOLEAN NOT NULL DEFAULT false,
    photo_url     VARCHAR(400),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_contact CHECK (email IS NOT NULL OR telephone IS NOT NULL)
);

CREATE TABLE IF NOT EXISTS proprietaires (
    user_id        UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    type_bailleur  VARCHAR(20) NOT NULL DEFAULT 'particulier',
    raison_sociale VARCHAR(180),
    piece_identite VARCHAR(400),
    note_moyenne   NUMERIC(3,2) DEFAULT 0,
    nb_avis        INT DEFAULT 0
);

-- =============================================================================
--  DOMAINE 3 — BIENS
-- =============================================================================
CREATE TABLE IF NOT EXISTS property_types (
    id      SERIAL PRIMARY KEY,
    code    VARCHAR(40) NOT NULL UNIQUE,
    libelle VARCHAR(80) NOT NULL
);

CREATE TABLE IF NOT EXISTS proprietes (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    proprietaire_id  UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    property_type_id INT  NOT NULL REFERENCES property_types(id),
    titre            VARCHAR(200) NOT NULL,
    description      TEXT,

    quartier_id      INT NOT NULL REFERENCES quartiers(id),
    adresse_precise  VARCHAR(255),
    latitude         DOUBLE PRECISION,
    longitude        DOUBLE PRECISION,

    nb_chambres      SMALLINT NOT NULL DEFAULT 0,
    nb_salons        SMALLINT NOT NULL DEFAULT 1,
    nb_salles_bain   SMALLINT DEFAULT 1,
    nb_cuisines      SMALLINT DEFAULT 1,
    surface_m2       NUMERIC(7,2),
    etage            SMALLINT,
    meuble           BOOLEAN DEFAULT false,

    mode_location    mode_location NOT NULL,
    capacite_voyageurs SMALLINT,

    statut           statut_annonce NOT NULL DEFAULT 'brouillon',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_prop_quartier ON proprietes (quartier_id);
CREATE INDEX IF NOT EXISTS idx_prop_type     ON proprietes (property_type_id);
CREATE INDEX IF NOT EXISTS idx_prop_statut   ON proprietes (statut);

CREATE TABLE IF NOT EXISTS propriete_photos (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    propriete_id   UUID NOT NULL REFERENCES proprietes(id) ON DELETE CASCADE,
    url            VARCHAR(400) NOT NULL,
    est_couverture BOOLEAN DEFAULT false,
    ordre          SMALLINT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS amenities (
    id      SERIAL PRIMARY KEY,
    code    VARCHAR(50) UNIQUE NOT NULL,
    libelle VARCHAR(100) NOT NULL,
    icone   VARCHAR(80)
);

CREATE TABLE IF NOT EXISTS propriete_amenities (
    propriete_id UUID REFERENCES proprietes(id) ON DELETE CASCADE,
    amenity_id   INT  REFERENCES amenities(id),
    PRIMARY KEY (propriete_id, amenity_id)
);

-- =============================================================================
--  DOMAINE 4 — TARIFICATION (double : mois / nuit)
-- =============================================================================
CREATE TABLE IF NOT EXISTS tarifs (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    propriete_id     UUID NOT NULL REFERENCES proprietes(id) ON DELETE CASCADE,
    unite            unite_tarif NOT NULL,
    montant          NUMERIC(12,2) NOT NULL,
    devise           CHAR(3) NOT NULL DEFAULT 'XOF',
    caution_mois     SMALLINT,
    charges_incluses BOOLEAN DEFAULT false,
    min_nuits        SMALLINT,
    frais_menage     NUMERIC(10,2),
    actif            BOOLEAN NOT NULL DEFAULT true,
    UNIQUE (propriete_id, unite)
);

CREATE TABLE IF NOT EXISTS tarifs_saisonniers (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tarif_id   UUID NOT NULL REFERENCES tarifs(id) ON DELETE CASCADE,
    date_debut DATE NOT NULL,
    date_fin   DATE NOT NULL,
    montant    NUMERIC(12,2) NOT NULL
);

-- =============================================================================
--  DOMAINE 5 — INTELLIGENCE DE ZONE (comparateur de quartiers)
-- =============================================================================
CREATE TABLE IF NOT EXISTS criteres (
    id           SERIAL PRIMARY KEY,
    code         VARCHAR(50) UNIQUE NOT NULL,
    libelle      VARCHAR(120) NOT NULL,
    categorie    VARCHAR(60),
    type_valeur  type_valeur NOT NULL DEFAULT 'score',
    unite        VARCHAR(30),
    poids_defaut NUMERIC(4,2) DEFAULT 1.0,
    description  TEXT
);

CREATE TABLE IF NOT EXISTS zone_scores (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    critere_id   INT NOT NULL REFERENCES criteres(id),
    region_id    INT REFERENCES regions(id),
    ville_id     INT REFERENCES villes(id),
    commune_id   INT REFERENCES communes(id),
    quartier_id  INT REFERENCES quartiers(id),
    score        NUMERIC(4,2),
    valeur_num   NUMERIC(14,2),
    valeur_texte TEXT,
    source       VARCHAR(160),
    fiabilite    SMALLINT DEFAULT 3,
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_un_niveau CHECK (
        num_nonnulls(region_id, ville_id, commune_id, quartier_id) = 1
    )
);
CREATE INDEX IF NOT EXISTS idx_zscore_quartier ON zone_scores (quartier_id, critere_id);

CREATE TABLE IF NOT EXISTS avis_quartier (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quartier_id INT NOT NULL REFERENCES quartiers(id),
    user_id     UUID REFERENCES users(id),
    note        SMALLINT CHECK (note BETWEEN 1 AND 5),
    commentaire TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =============================================================================
--  DOMAINE 6 — RÉSERVATION, PAIEMENT & COMMISSION
-- =============================================================================
CREATE TABLE IF NOT EXISTS reservations (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    propriete_id      UUID NOT NULL REFERENCES proprietes(id),
    locataire_id      UUID NOT NULL REFERENCES users(id),
    mode_location     mode_location NOT NULL,
    date_debut        DATE NOT NULL,
    date_fin          DATE,
    nb_unites         INT,
    montant_total     NUMERIC(12,2) NOT NULL,
    montant_en_ligne  NUMERIC(12,2) NOT NULL,
    montant_sur_place NUMERIC(12,2) NOT NULL DEFAULT 0,
    statut            statut_reservation NOT NULL DEFAULT 'en_attente_paiement',
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS paiements (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reservation_id    UUID NOT NULL REFERENCES reservations(id) ON DELETE CASCADE,
    type              type_paiement NOT NULL,
    methode           methode_paiement NOT NULL,
    montant           NUMERIC(12,2) NOT NULL,
    devise            CHAR(3) NOT NULL DEFAULT 'XOF',
    statut            statut_paiement NOT NULL DEFAULT 'initie',
    reference_externe VARCHAR(200),
    paye_le           TIMESTAMPTZ,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS commissions (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reservation_id UUID NOT NULL REFERENCES reservations(id) ON DELETE CASCADE,
    paiement_id    UUID REFERENCES paiements(id),
    base_calcul    NUMERIC(12,2) NOT NULL,
    taux           NUMERIC(5,2) NOT NULL,
    montant        NUMERIC(12,2) NOT NULL,
    statut         statut_commission NOT NULL DEFAULT 'due',
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS parametres_commission (
    id            SERIAL PRIMARY KEY,
    mode_location mode_location NOT NULL,
    type_frais    VARCHAR(30) NOT NULL,   -- 'pourcentage' | 'fixe'
    valeur        NUMERIC(12,2) NOT NULL,
    actif         BOOLEAN DEFAULT true
);

-- =============================================================================
--  DONNÉES DE DÉPART (SEED)
--  NB : le découpage commune/quartier de Lomé est INDICATIF — à valider.
-- =============================================================================
INSERT INTO regions (nom, slug, chef_lieu) VALUES
    ('Maritime', 'maritime', 'Lomé'),
    ('Plateaux', 'plateaux', 'Atakpamé'),
    ('Centrale', 'centrale', 'Sokodé'),
    ('Kara',     'kara',     'Kara'),
    ('Savanes',  'savanes',  'Dapaong')
ON CONFLICT (nom) DO NOTHING;

INSERT INTO villes (region_id, nom, slug)
SELECT r.id, v.nom, v.slug
FROM (VALUES ('Lomé','lome'), ('Tsévié','tsevie'), ('Aného','aneho')) AS v(nom, slug)
JOIN regions r ON r.slug = 'maritime'
ON CONFLICT (region_id, nom) DO NOTHING;

INSERT INTO communes (ville_id, nom, slug)
SELECT vl.id, c.nom, c.slug
FROM (VALUES
    ('Golfe 1','golfe-1'), ('Golfe 2','golfe-2'), ('Golfe 3','golfe-3'),
    ('Golfe 4','golfe-4'), ('Golfe 5','golfe-5'), ('Golfe 6','golfe-6'),
    ('Golfe 7','golfe-7')
) AS c(nom, slug)
JOIN villes vl ON vl.slug = 'lome'
ON CONFLICT (ville_id, nom) DO NOTHING;

INSERT INTO quartiers (commune_id, nom, slug, latitude, longitude)
SELECT cm.id, q.nom, q.slug, q.lat, q.lon
FROM (VALUES
    ('golfe-1','Bè',            'be',            6.1350, 1.2400),
    ('golfe-1','Nyékonakpoè',   'nyekonakpoe',   6.1250, 1.2100),
    ('golfe-2','Tokoin',        'tokoin',        6.1500, 1.2150),
    ('golfe-3','Kodjoviakopé',  'kodjoviakope',  6.1280, 1.1950),
    ('golfe-5','Adidogomé',     'adidogome',     6.1800, 1.1600),
    ('golfe-6','Baguida',       'baguida',       6.1700, 1.3200)
) AS q(commune_slug, nom, slug, lat, lon)
JOIN communes cm ON cm.slug = q.commune_slug
ON CONFLICT (commune_id, nom) DO NOTHING;

INSERT INTO property_types (code, libelle) VALUES
    ('villa','Villa'), ('appartement','Appartement'), ('studio','Studio'),
    ('chambre','Chambre'), ('maison','Maison basse'), ('bureau','Bureau'),
    ('terrain','Terrain')
ON CONFLICT (code) DO NOTHING;

INSERT INTO amenities (code, libelle) VALUES
    ('climatisation','Climatisation'),
    ('forage','Forage / eau courante'),
    ('groupe_electrogene','Groupe électrogène'),
    ('parking','Parking / garage'),
    ('wifi','Wi-Fi / fibre'),
    ('gardien','Gardien / sécurité'),
    ('cuisine_equipee','Cuisine équipée'),
    ('meuble','Meublé'),
    ('cour','Cour privée'),
    ('cloture','Clôture / mur')
ON CONFLICT (code) DO NOTHING;

INSERT INTO criteres (code, libelle, categorie, type_valeur, unite, description) VALUES
    ('securite',            'Sécurité',              'securite', 'score',     '/5',   'Niveau de sécurité ressenti et statistique'),
    ('accessibilite',       'Accessibilité',         'transport','score',     '/5',   'Facilité d''accès, état des routes'),
    ('transport',           'Transport en commun',   'transport','score',     '/5',   'Disponibilité taxis, motos, bus'),
    ('cout_vie',            'Coût de la vie',         'economie', 'score',     '/5',   'Niveau général des prix dans la zone'),
    ('loyer_moyen',         'Loyer moyen',            'economie', 'numerique', 'FCFA', 'Loyer mensuel moyen constaté'),
    ('dynamisme_economique','Dynamisme économique',   'economie', 'score',     '/5',   'Commerces, marchés, activité'),
    ('commodites',          'Commodités',             'confort',  'score',     '/5',   'Écoles, santé, marchés à proximité'),
    ('calme',               'Calme / tranquillité',   'confort',  'score',     '/5',   'Niveau de bruit et de tranquillité'),
    ('risque_inondation',   'Risque d''inondation',   'confort',  'score',     '/5',   'Exposition aux inondations (5 = faible risque)')
ON CONFLICT (code) DO NOTHING;

INSERT INTO parametres_commission (mode_location, type_frais, valeur, actif) VALUES
    ('courte_duree', 'pourcentage', 10.00,    true),
    ('longue_duree', 'fixe',        10000.00, true)
ON CONFLICT DO NOTHING;

-- =============================================================================
--  FIN DU SCRIPT
-- =============================================================================
