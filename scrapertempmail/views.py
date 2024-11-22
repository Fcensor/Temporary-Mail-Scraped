from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.timezone import now
import requests
from bs4 import BeautifulSoup
from .models import SessionInfo, EmailMessage


def get_client_ip(request):
    """Récupère l'adresse IP du client."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def scrape_10minutemail(request):
    url = "https://10minutemail.net/"

    # Récupérer les cookies existants
    session_cookies = request.COOKIES
    phpsessid = session_cookies.get('PHPSESSID', 1)  # Par défaut 1 si PHPSESSID est absent

    try:
        # Requête HTTP avec User-Agent et cookies existants
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, cookies=session_cookies)
        response.raise_for_status()
    except requests.RequestException as e:
        return JsonResponse({"error": f"Erreur lors de la requête vers la boîte mail : {str(e)}"}, status=500)

    # Copier les cookies de la réponse de 10MinuteMail
    backend_cookies = response.cookies.get_dict()

    # Analyse du contenu HTML
    soup = BeautifulSoup(response.content, 'html.parser')

    # Récupérer l'adresse email temporaire
    email_input = soup.find('input', {'id': 'fe_text'})
    email_address = email_input['value'] if email_input else None
    if not email_address:
        return JsonResponse({"error": "Impossible de récupérer l'adresse email temporaire."}, status=500)

    # Récupérer les emails dans la boîte de réception
    mail_table = soup.find('table', {'id': 'maillist'})
    mails = []
    if mail_table:
        rows = mail_table.find_all('tr')[1:]  # Exclure la ligne d'en-tête
        for row in rows:
            columns = row.find_all('td')
            if len(columns) >= 3:
                sender = columns[0].get_text(strip=True)  # Expéditeur

                # Extraire le sujet et le lien
                subject_element = columns[1].find('a')  # Sujet
                subject = subject_element.get_text(strip=True) if subject_element else "Sujet inconnu"
                link = subject_element['href'] if subject_element else None
                full_link = f"https://10minutemail.net/{link}" if link else None


                # Date
                date = columns[2].get_text(strip=True)  # Date

                # Récupérer le contenu complet du message
                content = None
                if full_link:
                    try:
                        email_response = requests.get(full_link, headers=headers, cookies=session_cookies)
                        email_response.raise_for_status()
                        email_soup = BeautifulSoup(email_response.content, 'html.parser')
                        content_element = email_soup.find('div', class_='mailinhtml')
                        content = content_element if content_element else "Contenu introuvable."
                    except requests.RequestException as e:
                        content = f"Erreur lors de la récupération du contenu : {str(e)}"

                mails.append({
                    'expediteur': sender,
                    'sujet': subject,
                    'date': date,
                    'lien': full_link,
                    'content': content,
                })

    # Gérer les données en base de données
    ip_address = get_client_ip(request)

    # Utiliser PHPSESSID ou 1 par défaut
    phpsessid = backend_cookies.get("PHPSESSID", phpsessid)

    if phpsessid:
        # Vérifier si une session existe déjà
        session_info, created = SessionInfo.objects.get_or_create(
            phpsessid=phpsessid,
            defaults={
                'email': email_address,
                'ip_address': ip_address,
                'start_time': now(),
            }
        )
        if not created:
            # Si la session existe déjà, incrémenter le compteur
            session_info.count += 1
            session_info.save()
    else:
        return JsonResponse({"error": "PHPSESSID manquant dans les cookies."}, status=400)

    # Ajouter les messages dans la base de données
    for mail in mails:
        # Vérifier si un email avec le même lien existe déjà
        if EmailMessage.objects.filter(link=mail['lien']).exists():
            continue  # Passer au prochain email si déjà existant

        # Télécharger le contenu brut si le lien existe
        content = None
        if mail['lien']:
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                email_response = requests.get(mail['lien'], headers=headers, cookies=session_cookies)
                email_response.raise_for_status()
                email_soup = BeautifulSoup(email_response.content, 'html.parser')
                content_element = email_soup.find('div', class_='mailinhtml')
                content = str(content_element) if content_element else None
            except requests.RequestException:
                pass

        # Ajouter le message à la base de données
        EmailMessage.objects.create(
            session=session_info,
            sender=mail['expediteur'],
            subject=mail['sujet'],
            date=mail['date'],
            link=mail['lien'],
            content=content
        )

    # Préparer la réponse avec les cookies copiés de la réponse 10MinuteMail
    response = render(request, 'results.html', {
        "adresse_email": email_address,
        "courriers_recus": mails,
    })
    for cookie_name, cookie_value in backend_cookies.items():
        response.set_cookie(cookie_name, cookie_value)
    return response

# Vue pour réinitialiser les cookies et recharger la page
@csrf_exempt
def reset_email(request):
    response = JsonResponse({"message": "Cookies réinitialisés."})
    for cookie in request.COOKIES:
        response.delete_cookie(cookie)
    return response


# Vue pour récupérer le contenu d'un email spécifique
def get_email_content(request):
    link = request.GET.get('link')
    if not link:
        return JsonResponse({"error": "L'URL de l'email est manquante."}, status=400)

    email = EmailMessage.objects.get(
        link=link
    )

    email_content_html = email.content or "Contenu non disponible"
    email_content_text = BeautifulSoup(email_content_html, 'html.parser').get_text(strip=True)

    return render(request, 'mail_content.html', {
        "contenu_html": email_content_html,
        "contenu_texte": email_content_text,
    })
