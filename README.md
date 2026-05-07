## 1. Structure du projet dans PyCharm
Ne mettez pas tout dans un seul fichier. Une structure "Modèle-Vue-Contrôleur" simplifiée vous évitera bien des maux de tête :

*   `main.py` : Point d'entrée de l'application.
*   `audio_engine.py` : Logique de lecture, filtrage et gestion du flux (backend).
*   `gui.py` : Définition de l'interface avec CustomTkinter (frontend).
*   `filters.py` : Fonctions mathématiques pour calculer les coefficients des filtres ($H(z)$).

---

## 2. Installé les bibliothèques sur la VM

sudo apt update

sudo apt install python3-tk

sudo apt install libportaudio2

sudo apt install libsndfile1 libsndfile1-dev
pip install --upgrade soundfile

### 2.1 INstallé le venv

pip install -r requirements.txt

---

## 3. Première étape : Le moteur audio
Avant de faire des curseurs brillants, assurez-vous de pouvoir lire un son et lui appliquer un filtre statique. 

**Le concept clé :** Vous devez utiliser un "callback" avec `sounddevice`. Au lieu de lire tout le fichier d'un coup, on lit des petits blocs de données (chunks) auxquels on applique l'équation de récurrence du filtre avant de les envoyer aux haut-parleurs.

---

## 4. Architecture des filtres (La partie Maths)
Pour votre documentation technique, vous devrez définir les filtres. Puisque vous utilisez `scipy.signal`, vous travaillerez principalement avec les fonctions :
*   `scipy.signal.butter` : Pour les filtres Passe-Haut / Passe-Bas (ordre 1 et 2).
*   `scipy.signal.iirfilter` : Pour les réjecteurs et sélecteurs (Band-stop / Band-pass).

**Conseil technique :** Pour le temps réel, évitez `lfilter` sur tout le fichier. Utilisez les coefficients $b$ et $a$ de votre filtre :
$$y[n] = \frac{1}{a_0} \left( \sum_{i=0}^{M} b_i x[n-i] - \sum_{j=1}^{N} a_j y[n-j] \right)$$

---

## 5. Construction de l'interface (CustomTkinter)
Commencez par une fenêtre simple. Voici l'ordre logique de développement de la GUI :
1.  **Le Layout :** Créez une barre latérale pour l'importation et le volume, et une zone centrale pour les filtres.
2.  **L'import :** Utilisez `tkinter.filedialog` pour récupérer le chemin du fichier `.wav`.
3.  **Les Widgets :**
    *   `CTkCheckBox` pour activer/désactiver le filtre.
    *   `CTkSlider` pour la fréquence de coupure ($f_c$).

---

## 6. Prochaines étapes immédiates
Voici votre "To-Do" pour la première séance de code :

1.  **Script de test :** Réussir à charger un son avec `soundfile` et le jouer avec `sounddevice`.
2.  **Prototype de filtre :** Appliquer un filtre passe-bas fixe de `scipy` sur ce son.
3.  **Liaison GUI :** Créer un bouton Play/Pause qui lance ce son.

### Attention au "Temps Réel"
Le "vrai" temps réel en Python peut être délicat à cause du GIL (Global Interpreter Lock). Si vous sentez que l'interface "freeze" pendant la lecture :
*   Utilisez le paramètre `callback` de `sounddevice.OutputStream`.
*   Assurez-vous que les calculs de coefficients de filtres ne sont faits **que** lorsque l'utilisateur bouge le curseur, pas à chaque échantillon audio.

**Par quoi souhaites-tu commencer ? Veux-tu un exemple de code pour la structure du moteur audio ou préfères-tu d'abord dessiner l'interface graphique ?**
```