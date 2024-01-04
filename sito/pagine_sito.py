from flask import Blueprint, render_template, request, redirect, url_for
from . import db
from flask_login import login_required, current_user
from .modelli import User, Classi
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from os import path, remove
from .refactor import refactor_file

from pathlib import Path

pagine_sito = Blueprint("pagine_sito", __name__)
ALLOWED_EXTENSIONS = set(["xlsx"])
FILE_ERRORE = path.join(Path.cwd(), "instance", "errore.txt")
FILE_VERSIONI = path.join(Path.cwd(), "instance", "versioni.txt")
LEGGI = "r"
RETURN_VALUE = "bottone"
ELIMINA_UTENTE = "elimina"
AGGIUNGI_CLASSE = "nuova"
ENTRA_NELLA_CLASSE = "raggiunti"
CONFERMA_CAMBIAMENTI_DATABASE = "datab"
VUOTO = ""


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def cronologia_da_user(utente):
    return utente.cronologia_studente


def user_da_nominativo(nominativo):
    return User.query.filter_by(nominativo=nominativo).first()


def user_da_email(email):
    return User.query.filter_by(email=email).first()


def classe_da_nome(classe_name):
    return Classi.query.filter_by(classe=classe_name).first()


def classe_da_id(classe_id):
    return Classi.query.filter_by(id=classe_id).first()


def ordina_studenti_in_modo_decrescente(classe, stagione):
    return sorted(
        classe.studenti,
        key=lambda studente: float(studente.punti.split(",")[stagione - 1]),
    )[::-1]


def elenco_utenti():
    return User.query.filter_by().all()


def elenco_studenti():
    return [utente for utente in User.query.filter_by().all() if not utente.admin_user]


def elenco_admin():
    return [utente for utente in User.query.filter_by().all() if utente.admin_user]


def elenco_classi():  # non si conta la classe degli admin
    return [
        classe for classe in Classi.query.filter_by().all() if classe.classe != "admin"
    ]


def elenco_di_tutte_le_classi():
    return Classi.query.filter_by().all()


def elenco_squadre():
    return set([x.squadra for x in elenco_studenti()])


def errore_accesso():
    return redirect(url_for("pagine_sito.home"))


@pagine_sito.route("/")
def home():
    try:
        return render_template(
            "home.html",
            user=current_user,
            classe_name=classe_da_id(current_user.classe_id).classe,
        )
    except:
        return render_template(
            "home.html", user=current_user, classe_name="Login_error"
        )


@pagine_sito.route("/classe/<classe_name>", methods=["GET", "POST"])
@login_required
def classe(classe_name):
    if not current_user.admin_user:
        classe = classe_da_id(current_user.classe_id)
    else:
        classe = classe_da_nome(classe_name)
    studenti = ordina_studenti_in_modo_decrescente(classe, 1)
    if current_user.admin_user is True and request.method == "POST":
        stagione = 1
        dati = request.form
        if "bottone" in dati:
            return render_template(
                "classe.html",
                user=current_user,
                classe=classe.classe,
                studenti=studenti,
            )
        if "elimina" in dati:
            db.session.delete(user_da_nominativo(dati["elimina"]))

        for nominativo in dati:
            try:
                punti_modificati = float(dati[nominativo])
                lista_punti_stagioni = list(
                    map(float, user_da_nominativo(nominativo).punti.split(","))
                )
                lista_punti_stagioni[stagione - 1] += punti_modificati
                user_da_nominativo(nominativo).punti = ",".join(
                    map(str, lista_punti_stagioni)
                )
            except ValueError:
                continue

        db.session.commit()
        studenti = ordina_studenti_in_modo_decrescente(classe, 1)
    return render_template(
        "classe.html", user=current_user, classe=classe.classe, studenti=studenti
    )


@pagine_sito.route("/regole")
def regole():
    try:
        return render_template(
            "regole.html",
            user=current_user,
            classe_name=classe_da_id(current_user.classe_id).classe,
        )
    except:
        return render_template(
            "regole.html", user=current_user, classe_name="Login_error"
        )


@pagine_sito.route("/admin_dashboard")
@login_required
def admin_dashboard():
    admin_user = current_user.admin_user
    errori = open(path.join(Path.cwd(), "instance", "errore.txt"), "r").read() == VUOTO
    if admin_user == 1:
        numero_degli_studenti = len(elenco_studenti())
        numero_delle_classi = len(elenco_classi())
        numero_degli_admin = len(elenco_admin())
        numero_delle_squadre = len(elenco_squadre())
        return render_template(
            "admin_dashboard.html",
            numero_studenti=numero_degli_studenti,
            numero_classi=numero_delle_classi,
            numero_admin=numero_degli_admin,
            numero_squadre=numero_delle_squadre,
            novità=elenco_utenti()[::-1][:7],
            errori=errori,
        )


@pagine_sito.route("/classi", methods=["GET", "POST"])
@login_required
def classi():
    if current_user.admin_user:
        classi = elenco_classi()

        if request.method == "POST":
            dati = request.form
            if dati[RETURN_VALUE] == ENTRA_NELLA_CLASSE:
                classe_name = dati.get("classe")
                classe = classe_da_nome(classe_name)
                return redirect(
                    url_for("pagine_sito.classe", classe_name=classe.classe)
                )

            if dati[RETURN_VALUE] == AGGIUNGI_CLASSE:
                classe_name = dati.get("classe")
                if classe_name != VUOTO and classe_name not in [
                    x.classe for x in elenco_di_tutte_le_classi()
                ]:
                    db.session.add(Classi(classe=classe_name))
                    db.session.commit()

            if dati[RETURN_VALUE] == CONFERMA_CAMBIAMENTI_DATABASE:
                file = request.files["filen"]
                if allowed_file(file.filename):
                    new_filename = "foglio.xlsx"

                    save_location = path.join(
                        path.join(Path.cwd(), "instance"), new_filename
                    )
                    file.save(save_location)
                    error_file = path.join(Path.cwd(), "instance", "errore.txt")
                    with open(error_file, "w") as f:
                        f.write(VUOTO)
                    refactor_file()
            return redirect(url_for("pagine_sito.classi"))

        return render_template("menu_classi.html", classi=classi)


@pagine_sito.route("/db_errori")
@login_required
def db_errori():
    if current_user.admin_user is False:
        return errore_accesso()
    return open(FILE_ERRORE, LEGGI).read().splitlines()


@pagine_sito.route("/versioni")
def versioni():
    return reversed(open(FILE_VERSIONI, LEGGI).read().splitlines())
