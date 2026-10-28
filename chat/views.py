import json
import re
import requests
import ipaddress

from urllib.parse import urljoin, urlparse
from socket import getaddrinfo

from bs4 import BeautifulSoup

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt

from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required

from .models import (
    Conversation,
    ChatMessage,
    ConversationInstruction
)

from .forms import RegisterForm

from groq import Groq


# =========================================================
# WEBSITE / WEB SETTINGS
# =========================================================

MAX_PAGES_TO_CRAWL = 6
MAX_CHARS_PER_PAGE = 5000
MAX_TOTAL_WEBSITE_CHARS = 18000

REQUEST_TIMEOUT = 15

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 "
    "(KHTML, like Gecko) "
    "Chrome/142.0 Safari/537.36"
)


# =========================================================
# WEBSITE URL DETECTOR
# =========================================================

def extract_url(text):

    if not isinstance(text, str):
        return None

    pattern = r'https?://[^\s<>"\']+'

    match = re.search(
        pattern,
        text
    )

    if match:

        return match.group(0).rstrip(
            ".,!?;:)"
        )

    return None


# =========================================================
# URL NORMALIZER
# =========================================================

def normalize_url(url):

    if not url:
        return None

    url = url.strip()

    if not url.startswith(("http://", "https://")):
        return None

    parsed = urlparse(url)

    if not parsed.scheme or not parsed.netloc:
        return None

    if parsed.scheme.lower() not in ["http", "https"]:
        return None

    # Remove fragments
    parsed = parsed._replace(fragment="")

    return parsed.geturl()


# =========================================================
# CHECK PRIVATE / LOCAL IP
# =========================================================

def is_private_or_local_hostname(hostname):

    if not hostname:
        return True

    hostname = hostname.lower().strip()

    # Block obvious local hostnames
    blocked_hosts = {
        "localhost",
        "localhost.localdomain",
        "ip6-localhost",
        "ip6-loopback",
    }

    if hostname in blocked_hosts:
        return True

    # Block local/internal host suffixes
    if hostname.endswith(".local"):
        return True

    if hostname.endswith(".internal"):
        return True

    # Direct IP address
    try:

        ip = ipaddress.ip_address(hostname)

        return (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        )

    except ValueError:
        pass

    # Resolve hostname and check returned IPs
    try:

        addresses = getaddrinfo(
            hostname,
            None
        )

        for address in addresses:

            ip_string = address[4][0]

            try:

                ip = ipaddress.ip_address(
                    ip_string
                )

                if (
                    ip.is_private
                    or ip.is_loopback
                    or ip.is_link_local
                    or ip.is_reserved
                    or ip.is_multicast
                    or ip.is_unspecified
                ):

                    return True

            except ValueError:

                continue

    except Exception:

        pass

    return False


# =========================================================
# VALIDATE WEBSITE URL
# =========================================================

def validate_website_url(url):

    url = normalize_url(url)

    if not url:

        return {
            "success": False,
            "error": "Invalid website URL."
        }

    parsed = urlparse(url)

    hostname = parsed.hostname

    if not hostname:

        return {
            "success": False,
            "error": "The website URL does not contain a valid hostname."
        }

    if is_private_or_local_hostname(hostname):

        return {
            "success": False,
            "error": (
                "For security reasons, local or private network "
                "addresses cannot be accessed."
            )
        }

    return {
        "success": True,
        "url": url
    }


# =========================================================
# SAME WEBSITE CHECK
# =========================================================

def is_same_website(base_url, target_url):

    try:

        base = urlparse(base_url)
        target = urlparse(target_url)

        base_host = (base.hostname or "").lower()
        target_host = (target.hostname or "").lower()

        if not base_host or not target_host:
            return False

        # Exact hostname match
        if target_host == base_host:
            return True

        # www.example.com and example.com
        if target_host.startswith("www."):
            target_host = target_host[4:]

        if base_host.startswith("www."):
            base_host = base_host[4:]

        return target_host == base_host

    except Exception:

        return False


# =========================================================
# CLEAN WEBSITE URL
# =========================================================

def clean_link(url):

    if not url:
        return None

    url = url.strip()

    # Remove fragment
    parsed = urlparse(url)

    parsed = parsed._replace(
        fragment=""
    )

    return parsed.geturl()


# =========================================================
# FETCH SINGLE WEBSITE PAGE
# =========================================================

def fetch_website_page(url):

    try:

        validation = validate_website_url(
            url
        )

        if not validation["success"]:

            return validation

        url = validation["url"]

        headers = {
            "User-Agent": USER_AGENT,
            "Accept": (
                "text/html,application/xhtml+xml,"
                "application/xml;q=0.9,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        }

        response = requests.get(
            url,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True
        )

        response.raise_for_status()

        # Check redirected URL
        final_url = response.url

        redirect_validation = validate_website_url(
            final_url
        )

        if not redirect_validation["success"]:

            return {
                "success": False,
                "error": (
                    "The website redirected to a "
                    "local or private address."
                )
            }

        # Only process HTML pages
        content_type = (
            response.headers.get(
                "Content-Type",
                ""
            ).lower()
        )

        if (
            "text/html" not in content_type
            and "application/xhtml+xml" not in content_type
        ):

            return {
                "success": False,
                "error": "The provided URL is not an HTML webpage."
            }

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        # -------------------------------------------------
        # REMOVE UNNECESSARY HTML
        # -------------------------------------------------

        for element in soup([
            "script",
            "style",
            "noscript",
            "svg",
            "iframe",
            "nav",
            "footer",
            "header",
            "form"
        ]):

            element.decompose()

        # -------------------------------------------------
        # TITLE
        # -------------------------------------------------

        title = ""

        if soup.title:

            title = soup.title.get_text(
                strip=True
            )

        # -------------------------------------------------
        # GET TEXT
        # -------------------------------------------------

        text = soup.get_text(
            separator=" ",
            strip=True
        )

        # -------------------------------------------------
        # CLEAN TEXT
        # -------------------------------------------------

        text = re.sub(
            r'\s+',
            ' ',
            text
        ).strip()

        # -------------------------------------------------
        # LIMIT PAGE CONTENT
        # -------------------------------------------------

        if len(text) > MAX_CHARS_PER_PAGE:

            text = text[:MAX_CHARS_PER_PAGE]

            text += (
                "\n\n[This page was truncated because "
                "it was very large.]"
            )

        # -------------------------------------------------
        # FIND LINKS
        # -------------------------------------------------

        links = []

        try:

            original_soup = BeautifulSoup(
                response.text,
                "html.parser"
            )

            for anchor in original_soup.find_all(
                "a",
                href=True
            ):

                href = anchor.get(
                    "href"
                )

                if not href:
                    continue

                # Ignore unwanted links
                if href.startswith(
                    (
                        "#",
                        "javascript:",
                        "mailto:",
                        "tel:",
                        "data:"
                    )
                ):
                    continue

                absolute_url = urljoin(
                    final_url,
                    href
                )

                absolute_url = clean_link(
                    absolute_url
                )

                if not absolute_url:
                    continue

                parsed_link = urlparse(
                    absolute_url
                )

                if parsed_link.scheme not in [
                    "http",
                    "https"
                ]:
                    continue

                # Only same website
                if not is_same_website(
                    final_url,
                    absolute_url
                ):
                    continue

                # Validate link
                if is_private_or_local_hostname(
                    parsed_link.hostname
                ):
                    continue

                if absolute_url not in links:

                    links.append(
                        absolute_url
                    )

        except Exception:

            links = []

        return {
            "success": True,
            "url": final_url,
            "title": title,
            "content": text,
            "links": links
        }

    except requests.exceptions.Timeout:

        return {
            "success": False,
            "error": (
                "The website took too long to respond."
            )
        }

    except requests.exceptions.TooManyRedirects:

        return {
            "success": False,
            "error": (
                "The website redirected too many times."
            )
        }

    except requests.exceptions.RequestException as e:

        return {
            "success": False,
            "error": (
                f"Could not access the website: {str(e)}"
            )
        }

    except Exception as e:

        return {
            "success": False,
            "error": (
                f"Website inspection failed: {str(e)}"
            )
        }


# =========================================================
# CHOOSE RELEVANT LINKS
# =========================================================

def rank_website_links(
    base_url,
    links,
    user_question
):

    if not links:

        return []

    question = (
        user_question or ""
    ).lower()

    # Words that usually indicate useful pages
    priority_words = [
        "about",
        "service",
        "services",
        "product",
        "products",
        "pricing",
        "price",
        "contact",
        "company",
        "team",
        "feature",
        "features",
        "solution",
        "solutions",
        "blog",
        "news",
        "documentation",
        "docs",
        "faq",
        "help",
        "support",
        "course",
        "courses",
        "shop",
        "store",
    ]

    # Words from user's question
    question_words = set(
        re.findall(
            r"[a-zA-Z0-9]{3,}",
            question
        )
    )

    scored_links = []

    for index, link in enumerate(links):

        try:

            parsed = urlparse(
                link
            )

            path = (
                parsed.path
                or ""
            ).lower()

            full_url = link.lower()

            score = 0

            # Priority page words
            for word in priority_words:

                if word in path:

                    score += 5

                elif word in full_url:

                    score += 2

            # Question words
            for word in question_words:

                if word in path:

                    score += 3

            # Shorter paths are often main pages
            if path.count("/") <= 2:

                score += 2

            # Avoid obvious files
            if re.search(
                r"\.(pdf|jpg|jpeg|png|gif|zip|rar|mp4|mp3|css|js)$",
                path
            ):

                score -= 10

            # Keep original order as tie-breaker
            scored_links.append(
                (
                    score,
                    -index,
                    link
                )
            )

        except Exception:

            continue

    scored_links.sort(
        reverse=True
    )

    return [
        item[2]
        for item in scored_links
    ]


# =========================================================
# CRAWL WEBSITE
# =========================================================

def crawl_website(
    start_url,
    user_question=None
):

    validation = validate_website_url(
        start_url
    )

    if not validation["success"]:

        return validation

    start_url = validation["url"]

    visited = set()

    pages = []

    pages_to_visit = [
        start_url
    ]

    total_chars = 0

    while (
        pages_to_visit
        and len(pages) < MAX_PAGES_TO_CRAWL
    ):

        current_url = pages_to_visit.pop(0)

        current_url = clean_link(
            current_url
        )

        if not current_url:
            continue

        if current_url in visited:
            continue

        # Same website only
        if not is_same_website(
            start_url,
            current_url
        ):
            continue

        visited.add(
            current_url
        )

        print(
            "================================="
        )

        print(
            "CRAWLING WEBSITE PAGE:",
            current_url
        )

        print(
            "================================="
        )

        page_data = fetch_website_page(
            current_url
        )

        if not page_data["success"]:

            print(
                "PAGE ERROR:",
                page_data["error"]
            )

            continue

        content = page_data.get(
            "content",
            ""
        )

        if not content:

            continue

        # Remaining character budget
        remaining_chars = (
            MAX_TOTAL_WEBSITE_CHARS
            - total_chars
        )

        if remaining_chars <= 0:

            break

        if len(content) > remaining_chars:

            content = content[
                :remaining_chars
            ]

        page_record = {
            "url": page_data["url"],
            "title": page_data.get(
                "title",
                ""
            ),
            "content": content
        }

        pages.append(
            page_record
        )

        total_chars += len(
            content
        )

        # -------------------------------------------------
        # DISCOVER MORE PAGES
        # -------------------------------------------------

        discovered_links = page_data.get(
            "links",
            []
        )

        ranked_links = rank_website_links(
            start_url,
            discovered_links,
            user_question
        )

        for link in ranked_links:

            if link in visited:
                continue

            if link in pages_to_visit:
                continue

            if not is_same_website(
                start_url,
                link
            ):
                continue

            pages_to_visit.append(
                link
            )

        # Keep queue under control
        pages_to_visit = pages_to_visit[
            :MAX_PAGES_TO_CRAWL * 3
        ]

    # -----------------------------------------------------
    # CHECK RESULT
    # -----------------------------------------------------

    if not pages:

        return {
            "success": False,
            "error": (
                "I could not read any useful content "
                "from the provided website."
            )
        }

    return {
        "success": True,
        "url": start_url,
        "pages": pages,
        "page_count": len(pages),
        "total_chars": total_chars
    }


# =========================================================
# FORMAT CRAWLED WEBSITE FOR AI
# =========================================================

def build_website_context(
    website_data
):

    if not website_data:
        return ""

    pages = website_data.get(
        "pages",
        []
    )

    context_parts = []

    for number, page in enumerate(
        pages,
        start=1
    ):

        title = (
            page.get("title")
            or "Untitled Page"
        )

        url = page.get(
            "url",
            ""
        )

        content = page.get(
            "content",
            ""
        )

        context_parts.append(
            f"""
==============================
WEBSITE PAGE {number}
==============================

Title:
{title}

URL:
{url}

Content:
{content}
"""
        )

    return "\n".join(
        context_parts
    )


# =========================================================
# USER INSTRUCTION DETECTOR
# =========================================================

def extract_user_instruction(text):

    if not isinstance(text, str):
        return None

    text = text.strip()

    patterns = [

        r"from now on[,:]?\s*(.*)",

        r"whenever i ask[,:]?\s*(.*)",

        r"when i ask[,:]?\s*(.*)",

        r"remember that[,:]?\s*(.*)",

        r"remember this[,:]?\s*(.*)",

        r"my instruction is[,:]?\s*(.*)",

    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            instruction = (
                match.group(1)
                .strip()
            )

            if instruction:

                return instruction

    return None


# =========================================================
# FORMAT USER INSTRUCTIONS
# =========================================================

def get_saved_instructions(
    conversation_obj
):

    saved_instructions = (
        ConversationInstruction.objects
        .filter(
            conversation=conversation_obj
        )
        .order_by("created_at")
    )

    instruction_text = ""

    for item in saved_instructions:

        instruction_text += (
            f"\n- {item.instruction}"
        )

    return instruction_text


# =========================================================
# HOME PAGE
# =========================================================

@login_required(
    login_url="login"
)
def home(request):

    return render(
        request,
        "chat/home.html"
    )


# =========================================================
# CHAT API
# =========================================================

@csrf_exempt
@login_required(
    login_url="login"
)
def chat(request):

    # ======================================
    # ONLY POST ALLOWED
    # ======================================

    if request.method != "POST":

        return JsonResponse(
            {
                "error":
                    "Only POST requests are allowed."
            },
            status=405
        )

    try:

        # ==================================
        # READ REQUEST
        # ==================================

        data = json.loads(
            request.body
        )

        messages_data = data.get(
            "messages",
            []
        )

        conversation_id = data.get(
            "conversation_id"
        )

        if not messages_data:

            return JsonResponse(
                {
                    "error":
                        "No messages received."
                },
                status=400
            )

        # ==================================
        # GET / CREATE CONVERSATION
        # ==================================

        conversation_obj = None

        if conversation_id:

            conversation_obj = (
                Conversation.objects.filter(
                    id=conversation_id,
                    user=request.user
                ).first()
            )

        # ----------------------------------
        # CREATE NEW CONVERSATION
        # ----------------------------------

        if conversation_obj is None:

            first_user_message = ""

            for message in messages_data:

                if (
                    message.get("role") == "user"
                    and message.get("content")
                ):

                    first_user_message = (
                        message.get(
                            "content"
                        ).strip()
                    )

                    break

            if first_user_message:

                title = (
                    first_user_message[:50]
                )

            else:

                title = "New Chat"

            conversation_obj = (
                Conversation.objects.create(
                    user=request.user,
                    title=title
                )
            )

        # ==================================
        # GROQ CLIENT
        # ==================================

        client = Groq(
            api_key=settings.GROQ_API_KEY
        )

        # ==================================
        # VALIDATE MESSAGES
        # ==================================

        valid_messages = []

        for message in messages_data:

            role = message.get(
                "role"
            )

            content = message.get(
                "content"
            )

            if (
                role in [
                    "user",
                    "assistant"
                ]
                and content
                and isinstance(
                    content,
                    str
                )
            ):

                valid_messages.append(
                    {
                        "role": role,
                        "content": content
                    }
                )

        if not valid_messages:

            return JsonResponse(
                {
                    "error":
                        "No valid messages received."
                },
                status=400
            )

        # ==================================
        # KEEP RECENT HISTORY
        # ==================================

        recent_messages = (
            valid_messages[-20:]
        )

        # ==================================
        # GET LATEST USER MESSAGE
        # ==================================

        latest_user_message = None

        for message in reversed(
            valid_messages
        ):

            if (
                message.get("role")
                == "user"
            ):

                latest_user_message = (
                    message.get(
                        "content"
                    )
                )

                break

        # ==================================
        # CHECK USER INSTRUCTION
        # ==================================

        if latest_user_message:

            instruction = (
                extract_user_instruction(
                    latest_user_message
                )
            )

            if instruction:

                ConversationInstruction.objects.create(
                    conversation=conversation_obj,
                    instruction=instruction
                )

                print(
                    "================================="
                )

                print(
                    "NEW USER INSTRUCTION:",
                    instruction
                )

                print(
                    "================================="
                )

        # ==================================
        # LOAD SAVED INSTRUCTIONS
        # ==================================

        instruction_text = (
            get_saved_instructions(
                conversation_obj
            )
        )

        # ==================================
        # CHECK FOR WEBSITE URL
        # ==================================

        website_data = None

        website_url = None

        if latest_user_message:

            website_url = extract_url(
                latest_user_message
            )

            if website_url:

                print(
                    "================================="
                )

                print(
                    "WEBSITE URL DETECTED:",
                    website_url
                )

                print(
                    "================================="
                )

                # ----------------------------------
                # CRAWL WEBSITE
                # ----------------------------------

                website_data = crawl_website(
                    website_url,
                    latest_user_message
                )

                if not website_data["success"]:

                    return JsonResponse(
                        {
                            "error":
                                website_data["error"]
                        },
                        status=400
                    )

                print(
                    "================================="
                )

                print(
                    "WEBSITE CRAWL COMPLETE"
                )

                print(
                    "PAGES:",
                    website_data.get(
                        "page_count",
                        0
                    )
                )

                print(
                    "CHARACTERS:",
                    website_data.get(
                        "total_chars",
                        0
                    )
                )

                print(
                    "================================="
                )

        # ==================================
        # NORMAL SYSTEM PROMPT
        # ==================================

        system_prompt = (

            "You are a friendly AI assistant. "

            "Give clear, short and useful answers. "

            "Use simple English. "

            "For normal questions, answer in "
            "2 to 3 sentences. "

            "For technical questions, explain "
            "step by step but stay concise. "

            "Use bullet points when useful. "

            "Only give detailed or long answers "
            "when the user asks for them. "

            "Do not repeat the user's question. "

            "Do not add unnecessary introductions "
            "or conclusions. "

            "When providing code, use proper "
            "Markdown code blocks. "

            "Understand casual language, slang, "
            "vulgar words and informal wording. "

            "Always understand the user's actual "
            "question or intent. "

            "Do not insult the user back. "

            "Remember instructions given by the "
            "user during the conversation. "

            "Follow valid user instructions when "
            "answering later questions. "

            "Do not forget earlier instructions "
            "simply because a new question was asked. "

            "\n\nUSER INSTRUCTIONS:\n"

            + (
                instruction_text
                if instruction_text
                else "No special instructions."
            )
        )

        # ==================================
        # WEBSITE MODE
        # ==================================

        if website_data:

            website_context = (
                build_website_context(
                    website_data
                )
            )

            crawled_pages = website_data.get(
                "pages",
                []
            )

            source_urls = []

            for page in crawled_pages:

                page_url = page.get(
                    "url"
                )

                if (
                    page_url
                    and page_url not in source_urls
                ):

                    source_urls.append(
                        page_url
                    )

            sources_text = "\n".join(
                source_urls
            )

            system_prompt = (

                "You are a website research "
                "and analysis assistant. "

                "The user provided a website URL. "

                "The website has been crawled by "
                "the application and the page "
                "content is provided below. "

                "Use the website content as the "
                "primary and authoritative source "
                "for website-specific questions. "

                "Do NOT invent information that "
                "is not contained in the provided "
                "website content. "

                "Do NOT pretend that you read a page "
                "that was not provided. "

                "If the requested information is "
                "not available in the crawled content, "
                "clearly say that the information "
                "was not found on the provided website. "

                "You may summarize, explain, compare, "
                "organize and describe information "
                "contained in the website pages. "

                "When useful, mention the page URL "
                "where the information came from. "

                "If the user asks for everything "
                "about the website, provide a useful "
                "structured summary of the information "
                "found across the crawled pages. "

                "Keep the answer concise unless the "
                "user asks for a detailed answer. "

                "\n\nUSER INSTRUCTIONS:\n"

                + (
                    instruction_text
                    if instruction_text
                    else "No special instructions."
                )

                + "\n\nSTARTING WEBSITE URL:\n"

                + website_data.get(
                    "url",
                    website_url or ""
                )

                + "\n\nCRAWLED WEBSITE SOURCES:\n"

                + sources_text

                + "\n\nCRAWLED WEBSITE CONTENT:\n"

                + website_context
            )

        # ==================================
        # BUILD CONVERSATION
        # ==================================

        conversation = [

            {
                "role": "system",
                "content": system_prompt
            }

        ]

        conversation.extend(
            recent_messages
        )

        # ==================================
        # GROQ REQUEST
        # ==================================

        completion = client.chat.completions.create(

            model="openai/gpt-oss-120b",

            messages=conversation,

            temperature=0.3,

            max_tokens=800
        )

        # ==================================
        # GET AI RESPONSE
        # ==================================

        ai_response = (
            completion
            .choices[0]
            .message
            .content
        )

        # ==================================
        # CHECK RESPONSE
        # ==================================

        if not ai_response:

            return JsonResponse(
                {
                    "error":
                        "The AI returned an empty response."
                },
                status=500
            )

        # ==================================
        # SAVE USER MESSAGE
        # ==================================

        latest_user_message = None

        for message in reversed(
            valid_messages
        ):

            if (
                message.get("role")
                == "user"
            ):

                latest_user_message = (
                    message.get(
                        "content"
                    )
                )

                break

        if latest_user_message:

            ChatMessage.objects.create(

                conversation=conversation_obj,

                role="user",

                content=latest_user_message

            )

        # ==================================
        # SAVE AI RESPONSE
        # ==================================

        ChatMessage.objects.create(

            conversation=conversation_obj,

            role="assistant",

            content=ai_response

        )

        # ==================================
        # UPDATE CONVERSATION
        # ==================================

        conversation_obj.save()

        # ==================================
        # BUILD SOURCES
        # ==================================

        sources = []

        if website_data:

            for page in website_data.get(
                "pages",
                []
            ):

                page_url = page.get(
                    "url"
                )

                page_title = (
                    page.get("title")
                    or "Website page"
                )

                if page_url:

                    sources.append(
                        {
                            "title": page_title,
                            "url": page_url
                        }
                    )

        # ==================================
        # SEND RESPONSE
        # ==================================

        return JsonResponse(
            {
                "response": ai_response,

                "conversation_id":
                    conversation_obj.id,

                "conversation_title":
                    conversation_obj.title,

                "sources":
                    sources
            }
        )

    # ======================================
    # INVALID JSON
    # ======================================

    except json.JSONDecodeError:

        return JsonResponse(
            {
                "error":
                    "Invalid JSON request."
            },
            status=400
        )

    # ======================================
    # SERVER / GROQ ERROR
    # ======================================

    except Exception as e:

        print(
            "================================="
        )

        print(
            "CHAT / GROQ ERROR:",
            e
        )

        print(
            "================================="
        )

        return JsonResponse(
            {
                "error":
                    "The chatbot encountered an error.",
                "details":
                    str(e)
            },
            status=500
        )


# =========================================================
# CONVERSATIONS
# =========================================================

@login_required(
    login_url="login"
)
def conversations(request):

    if request.method != "GET":

        return JsonResponse(
            {
                "error":
                    "Only GET requests are allowed."
            },
            status=405
        )

    user_conversations = (
        Conversation.objects
        .filter(
            user=request.user
        )
        .order_by(
            "-updated_at"
        )
    )

    conversation_list = []

    for conversation in user_conversations:

        conversation_list.append(
            {
                "id":
                    conversation.id,

                "title":
                    conversation.title,

                "created_at":
                    conversation.created_at.strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),

                "updated_at":
                    conversation.updated_at.strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
            }
        )

    return JsonResponse(
        {
            "conversations":
                conversation_list
        }
    )


# =========================================================
# CONVERSATION DETAIL
# =========================================================

@login_required(
    login_url="login"
)
def conversation_detail(
    request,
    conversation_id
):

    if request.method != "GET":

        return JsonResponse(
            {
                "error":
                    "Only GET requests are allowed."
            },
            status=405
        )

    conversation_obj = (
        Conversation.objects
        .filter(
            id=conversation_id,
            user=request.user
        )
        .first()
    )

    if conversation_obj is None:

        return JsonResponse(
            {
                "error":
                    "Conversation not found."
            },
            status=404
        )

    messages_list = []

    chat_messages = (
        conversation_obj.messages
        .order_by(
            "created_at"
        )
    )

    for message in chat_messages:

        messages_list.append(
            {
                "id":
                    message.id,

                "role":
                    message.role,

                "content":
                    message.content,

                "created_at":
                    message.created_at.strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
            }
        )

    return JsonResponse(
        {
            "conversation": {

                "id":
                    conversation_obj.id,

                "title":
                    conversation_obj.title,

                "created_at":
                    conversation_obj.created_at.strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),

                "updated_at":
                    conversation_obj.updated_at.strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
            },

            "messages":
                messages_list
        }
    )


# =========================================================
# DELETE CONVERSATION
# =========================================================

@login_required(
    login_url="login"
)
def delete_conversation(
    request,
    conversation_id
):

    if request.method != "DELETE":

        return JsonResponse(
            {
                "error":
                    "Only DELETE requests are allowed."
            },
            status=405
        )

    conversation_obj = (
        Conversation.objects
        .filter(
            id=conversation_id,
            user=request.user
        )
        .first()
    )

    if conversation_obj is None:

        return JsonResponse(
            {
                "error":
                    "Conversation not found."
            },
            status=404
        )

    conversation_obj.delete()

    return JsonResponse(
        {
            "success": True,

            "message":
                "Conversation deleted successfully."
        }
    )


# =========================================================
# REGISTER
# =========================================================

def register_view(request):

    if request.user.is_authenticated:

        return redirect(
            "home"
        )

    if request.method == "POST":

        username = request.POST.get(
            "username",
            ""
        ).strip()

        email = request.POST.get(
            "email",
            ""
        ).strip()

        password = request.POST.get(
            "password",
            ""
        )

        password2 = request.POST.get(
            "password2",
            ""
        )

        if (
            not username
            or not email
            or not password
            or not password2
        ):

            messages.error(
                request,
                "Please fill in all fields."
            )

            return redirect(
                "register"
            )

        if password != password2:

            messages.error(
                request,
                "Passwords do not match."
            )

            return redirect(
                "register"
            )

        if User.objects.filter(
            username=username
        ).exists():

            messages.error(
                request,
                "Username already exists."
            )

            return redirect(
                "register"
            )

        if User.objects.filter(
            email=email
        ).exists():

            messages.error(
                request,
                "Email is already registered."
            )

            return redirect(
                "register"
            )

        user = User.objects.create_user(

            username=username,

            email=email,

            password=password
        )

        login(
            request,
            user
        )

        return redirect(
            "home"
        )

    return render(
        request,
        "chat/register.html"
    )


# =========================================================
# LOGIN
# =========================================================

def login_view(request):

    if request.user.is_authenticated:

        return redirect(
            "home"
        )

    if request.method == "POST":

        username = request.POST.get(
            "username",
            ""
        ).strip()

        password = request.POST.get(
            "password",
            ""
        )

        user = authenticate(

            request,

            username=username,

            password=password
        )

        if user is not None:

            login(
                request,
                user
            )

            return redirect(
                "home"
            )

        messages.error(
            request,
            "Invalid username or password."
        )

        return redirect(
            "login"
        )

    return render(
        request,
        "chat/login.html"
    )


# =========================================================
# LOGOUT
# =========================================================

def logout_view(request):

    logout(
        request
    )

    return redirect(
        "login"
    )
@csrf_exempt
def widget_chat(request):

    # ==========================================
    # ONLY POST ALLOWED
    # ==========================================

    if request.method != "POST":
        return JsonResponse(
            {
                "error": "Only POST requests are allowed."
            },
            status=405
        )

    try:

        # ==========================================
        # READ JSON
        # ==========================================

        data = json.loads(
            request.body
        )

        message = data.get(
            "message",
            ""
        ).strip()

        website_url = data.get(
            "website_url",
            ""
        ).strip()

        # ==========================================
        # VALIDATE MESSAGE
        # ==========================================

        if not message:

            return JsonResponse(
                {
                    "error": "Message is required."
                },
                status=400
            )

        # ==========================================
        # VALIDATE WEBSITE URL
        # ==========================================

        validation = validate_website_url(
            website_url
        )

        if not validation["success"]:

            return JsonResponse(
                {
                    "error":
                        validation["error"]
                },
                status=400
            )

        website_url = validation["url"]

        # ==========================================
        # CRAWL WEBSITE
        # ==========================================

        print(
            "================================="
        )

        print(
            "WIDGET WEBSITE:",
            website_url
        )

        print(
            "WIDGET QUESTION:",
            message
        )

        print(
            "================================="
        )

        website_data = crawl_website(
            website_url,
            message
        )

        # ==========================================
        # CHECK CRAWL
        # ==========================================

        if not website_data["success"]:

            return JsonResponse(
                {
                    "error":
                        website_data["error"]
                },
                status=400
            )

        # ==========================================
        # BUILD WEBSITE CONTEXT
        # ==========================================

        website_context = (
            build_website_context(
                website_data
            )
        )

        # ==========================================
        # GROQ CLIENT
        # ==========================================

        client = Groq(
            api_key=settings.GROQ_API_KEY
        )

        # ==========================================
        # WEBSITE-ONLY SYSTEM PROMPT
        # ==========================================

        system_prompt = (
            "You are an AI website assistant. "

            "You are answering questions about "
            "the website provided below. "

            "IMPORTANT RULES: "

            "1. Answer ONLY using information "
            "contained in the provided website content. "

            "2. Never invent information. "

            "3. Never use outside knowledge. "

            "4. If the answer cannot be found "
            "in the website content, say exactly: "
            "\"This information is not available "
            "on this website.\" "

            "5. You may summarize or explain "
            "information from the website. "

            "6. Keep answers clear and concise. "

            "\n\n"
            "WEBSITE URL:\n"
            + website_url

            + "\n\n"
            "WEBSITE CONTENT:\n"
            + website_context
        )

        # ==========================================
        # GROQ REQUEST
        # ==========================================

        completion = client.chat.completions.create(
            model="openai/gpt-oss-120b",

            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": message
                }
            ],

            temperature=0.2,
            max_tokens=500
        )

        # ==========================================
        # GET AI RESPONSE
        # ==========================================

        ai_response = (
            completion
            .choices[0]
            .message
            .content
        )

        # ==========================================
        # CHECK RESPONSE
        # ==========================================

        if not ai_response:

            return JsonResponse(
                {
                    "error":
                        "The AI returned an empty response."
                },
                status=500
            )

        # ==========================================
        # RESPONSE
        # ==========================================

        return JsonResponse(
            {
                "success": True,

                "response":
                    ai_response,

                "website_url":
                    website_url,

                "pages_crawled":
                    website_data.get(
                        "page_count",
                        0
                    )
            }
        )

    # ==========================================
    # INVALID JSON
    # ==========================================

    except json.JSONDecodeError:

        return JsonResponse(
            {
                "error":
                    "Invalid JSON request."
            },
            status=400
        )

    # ==========================================
    # SERVER ERROR
    # ==========================================

    except Exception as e:

        print(
            "================================="
        )

        print(
            "WIDGET ERROR:",
            e
        )

        print(
            "================================="
        )

        return JsonResponse(
            {
                "error":
                    "The website chatbot encountered an error.",

                "details":
                    str(e)
            },
            status=500
        )