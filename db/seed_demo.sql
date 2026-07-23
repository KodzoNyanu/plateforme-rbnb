-- =============================================================================
--  DONNÉES DE DÉMONSTRATION (facultatives, ré-exécutables)
--  Un propriétaire, quelques annonces avec double tarification, et des
--  scores de quartiers pour alimenter le comparateur.
-- =============================================================================

-- ── Propriétaire de démo ──
INSERT INTO users (id, nom_complet, telephone, role, is_verified)
VALUES ('11111111-1111-1111-1111-111111111111', 'Koffi Demo (Bailleur)', '+22890000000', 'proprietaire', true)
ON CONFLICT (id) DO NOTHING;

INSERT INTO proprietaires (user_id, type_bailleur)
VALUES ('11111111-1111-1111-1111-111111111111', 'particulier')
ON CONFLICT (user_id) DO NOTHING;

-- ── Annonces (UUID fixes pour ré-exécution) ──
INSERT INTO proprietes (id, proprietaire_id, property_type_id, titre, description,
                        quartier_id, nb_chambres, nb_salons, surface_m2, meuble,
                        mode_location, capacite_voyageurs, statut)
SELECT v.id::uuid, '11111111-1111-1111-1111-111111111111', pt.id, v.titre, v.descr,
       q.id, v.ch, 1, v.surf, v.meuble, v.mode::mode_location, v.cap, 'publiee'
FROM (VALUES
    ('a1111111-1111-1111-1111-111111111111','villa',      'tokoin',      'Villa 3 chambres salon à Tokoin', 'Belle villa avec cour et parking.',        3, 180, false, 'longue_duree', NULL),
    ('a2222222-2222-2222-2222-222222222222','appartement','be',          'Appartement 2 chambres salon à Bè', 'Appartement lumineux proche du marché.',  2, 90,  false, 'longue_duree', NULL),
    ('a3333333-3333-3333-3333-333333333333','studio',     'kodjoviakope','Studio meublé bord de mer',        'Idéal court séjour, tout équipé.',        0, 35,  true,  'courte_duree', 2),
    ('a4444444-4444-4444-4444-444444444444','villa',      'baguida',     'Villa meublée avec piscine (nuitée)', 'Parfaite pour vacances en famille.',   4, 320, true,  'les_deux',     8),
    ('a5555555-5555-5555-5555-555555555555','appartement','adidogome',   'Appartement 2 chambres salon Adidogomé','Quartier calme et résidentiel.',    2, 85,  false, 'longue_duree', NULL)
) AS v(id, type_code, quartier_slug, titre, descr, ch, surf, meuble, mode, cap)
JOIN property_types pt ON pt.code = v.type_code
JOIN quartiers q       ON q.slug  = v.quartier_slug
ON CONFLICT (id) DO NOTHING;

-- ── Tarifs (double tarification) ──
-- Loyers au mois
INSERT INTO tarifs (propriete_id, unite, montant, caution_mois)
SELECT v.pid::uuid, 'mois', v.montant, v.caution
FROM (VALUES
    ('a1111111-1111-1111-1111-111111111111', 150000, 6),
    ('a2222222-2222-2222-2222-222222222222', 80000,  6),
    ('a4444444-4444-4444-4444-444444444444', 600000, 3),
    ('a5555555-5555-5555-5555-555555555555', 90000,  6)
) AS v(pid, montant, caution)
ON CONFLICT (propriete_id, unite) DO NOTHING;

-- Prix à la nuitée
INSERT INTO tarifs (propriete_id, unite, montant, min_nuits, frais_menage)
SELECT v.pid::uuid, 'nuit', v.montant, v.minn, v.menage
FROM (VALUES
    ('a3333333-3333-3333-3333-333333333333', 15000, 1, 5000),
    ('a4444444-4444-4444-4444-444444444444', 45000, 2, 15000)
) AS v(pid, montant, minn, menage)
ON CONFLICT (propriete_id, unite) DO NOTHING;

-- ── Photos de démonstration (placeholders ; à remplacer par de vraies photos) ──
INSERT INTO propriete_photos (propriete_id, url, est_couverture, ordre)
SELECT v.pid::uuid, v.url, true, 0
FROM (VALUES
    ('a1111111-1111-1111-1111-111111111111','https://picsum.photos/seed/villatokoin/1000/600'),
    ('a2222222-2222-2222-2222-222222222222','https://picsum.photos/seed/apptbe/1000/600'),
    ('a3333333-3333-3333-3333-333333333333','https://picsum.photos/seed/studiokodjo/1000/600'),
    ('a4444444-4444-4444-4444-444444444444','https://picsum.photos/seed/villabaguida/1000/600'),
    ('a5555555-5555-5555-5555-555555555555','https://picsum.photos/seed/apptadidogome/1000/600')
) AS v(pid, url)
WHERE NOT EXISTS (
    SELECT 1 FROM propriete_photos ph WHERE ph.propriete_id = v.pid::uuid
);

-- ── Scores de quartiers (pour le comparateur) ──
INSERT INTO zone_scores (critere_id, quartier_id, score, source, fiabilite)
SELECT cr.id, q.id, v.score, 'seed_demo', 3
FROM (VALUES
    ('tokoin',      'securite', 3.5), ('tokoin',      'accessibilite', 4.5), ('tokoin',      'transport', 4.5),
    ('tokoin',      'cout_vie', 3.0), ('tokoin',      'dynamisme_economique', 4.5), ('tokoin',      'commodites', 4.0),
    ('tokoin',      'calme', 2.5), ('tokoin',      'risque_inondation', 3.0),
    ('be',          'securite', 3.0), ('be',          'accessibilite', 4.0), ('be',          'transport', 4.0),
    ('be',          'cout_vie', 2.5), ('be',          'dynamisme_economique', 5.0), ('be',          'commodites', 4.0),
    ('be',          'calme', 2.0), ('be',          'risque_inondation', 2.0),
    ('adidogome',   'securite', 4.0), ('adidogome',   'accessibilite', 3.0), ('adidogome',   'transport', 3.0),
    ('adidogome',   'cout_vie', 4.0), ('adidogome',   'dynamisme_economique', 3.0), ('adidogome',   'commodites', 3.5),
    ('adidogome',   'calme', 4.5), ('adidogome',   'risque_inondation', 4.0),
    ('baguida',     'securite', 4.0), ('baguida',     'accessibilite', 3.0), ('baguida',     'transport', 2.5),
    ('baguida',     'cout_vie', 3.5), ('baguida',     'dynamisme_economique', 2.5), ('baguida',     'commodites', 3.0),
    ('baguida',     'calme', 4.5), ('baguida',     'risque_inondation', 4.5)
) AS v(qslug, ccode, score)
JOIN quartiers q ON q.slug  = v.qslug
JOIN criteres  cr ON cr.code = v.ccode
WHERE NOT EXISTS (
    SELECT 1 FROM zone_scores z WHERE z.quartier_id = q.id AND z.critere_id = cr.id
);
