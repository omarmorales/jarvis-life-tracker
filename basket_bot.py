import os
import io
import json
import logging
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

# Telegram Imports
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)

# OpenAI Import
from openai import AsyncOpenAI

# Database Integration
import database

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger("basket_bot")

# Initialize OpenAI client
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# In-memory dictionary to store conversation history per chat_id
basket_sessions = {}

# Security: Helper to check if a Telegram user is authorized (supports comma-separated IDs)
def is_basket_user_authorized(user_id: int) -> bool:
    """Checks if the given user_id is in the list of authorized BasketBot administrators.
    
    Supports comma-separated IDs in BASKET_ALLOWED_USER_IDS (e.g. '12345678,87654321').
    If BASKET_ALLOWED_USER_IDS is not configured, the bot remains open to any user for testing.
    """
    allowed_raw = os.getenv("BASKET_ALLOWED_USER_IDS") or os.getenv("BASKET_ALLOWED_USER_ID")
    if not allowed_raw or str(allowed_raw).strip() == "" or str(allowed_raw).strip() == "your_telegram_user_id_here":
        # Abierto por defecto para pruebas si no se configura explícitamente una lista
        return True

    allowed_ids = set()
    for part in str(allowed_raw).split(","):
        part = part.strip()
        if part.isdigit():
            allowed_ids.add(int(part))

    return (user_id in allowed_ids) if allowed_ids else True

# ==========================================
# OPENAI TOOLS DEFINITION FOR BASKETBALL
# ==========================================

basket_tools = [
    {
        "type": "function",
        "function": {
            "name": "crear_torneo",
            "description": "Crea un nuevo torneo de basketball con su costo total o desglosado (inscripción + arbitrajes).",
            "parameters": {
                "type": "object",
                "properties": {
                    "nombre": {
                        "type": "string",
                        "description": "Nombre del torneo (ej. 'Torneo Ledom Jun - Nov 2026', 'Liga Dominical')."
                    },
                    "equipo": {
                        "type": "string",
                        "description": "Nombre del equipo (ej. 'Toros', 'Celtics'). Por defecto 'Mi Equipo'."
                    },
                    "costo_total": {
                        "type": "number",
                        "description": "Costo total global del torneo (inscripción + todos los arbitrajes)."
                    },
                    "inscripcion": {
                        "type": "number",
                        "description": "Costo específico de la inscripción si se desglosa."
                    },
                    "arbitrajes_total": {
                        "type": "number",
                        "description": "Costo total acumulado de arbitrajes si se desglosa."
                    },
                    "forzar_creacion": {
                        "type": "boolean",
                        "description": "True solo si el usuario confirmó explícitamente que desea crear un torneo nuevo a pesar de que exista uno parecido."
                    }
                },
                "required": ["nombre"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "actualizar_costo_torneo",
            "description": "Actualiza o modifica el costo total, costo de inscripción, arbitrajes o equipo de un torneo existente (recalcula automáticamente las cuotas de los jugadores).",
            "parameters": {
                "type": "object",
                "properties": {
                    "torneo": {
                        "type": "string",
                        "description": "Nombre o ID del torneo existente que se desea modificar (ej. 'Ledom', 'Ledom 2026')."
                    },
                    "costo_total": {
                        "type": "number",
                        "description": "Nuevo costo total global del torneo."
                    },
                    "inscripcion": {
                        "type": "number",
                        "description": "Nuevo costo de inscripción si se desglosa."
                    },
                    "arbitrajes_total": {
                        "type": "number",
                        "description": "Nuevo costo total de arbitrajes si se desglosa."
                    },
                    "equipo": {
                        "type": "string",
                        "description": "Nuevo nombre del equipo si se desea cambiar."
                    }
                },
                "required": ["torneo"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "agregar_jugadores",
            "description": "Agrega uno o varios jugadores al roster de un torneo (admite nombres o nombres con número, ej. ['Carlos #7', 'Omar #23', 'Memo']) y recalcula la cuota equitativa automáticamente.",
            "parameters": {
                "type": "object",
                "properties": {
                    "torneo": {
                        "type": "string",
                        "description": "Nombre o ID del torneo donde se agregarán."
                    },
                    "jugadores": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Lista de nombres o nombres con número de los jugadores a inscribir (ej. ['Carlos #7', 'Juan #10', 'Memo'])."
                    }
                },
                "required": ["torneo", "jugadores"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "asignar_numero_jugador",
            "description": "Asigna o cambia el número de camiseta/jersey de un jugador (ej. 'Omar lleva el número 23').",
            "parameters": {
                "type": "object",
                "properties": {
                    "jugador": {
                        "type": "string",
                        "description": "Nombre del jugador."
                    },
                    "numero": {
                        "type": "integer",
                        "description": "Número de camiseta/jersey del jugador (ej. 23, 7, 0)."
                    },
                    "torneo": {
                        "type": "string",
                        "description": "Opcional: Nombre o ID del torneo si el número es específico para ese torneo."
                    }
                },
                "required": ["jugador", "numero"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "eliminar_torneo",
            "description": "Elimina permanentemente un torneo y todos sus datos asociados (partidos, récord, pagos y cuotas).",
            "parameters": {
                "type": "object",
                "properties": {
                    "torneo": {
                        "type": "string",
                        "description": "Nombre o ID del torneo a eliminar."
                    },
                    "confirmar": {
                        "type": "boolean",
                        "description": "Debe ser true para proceder con la eliminación definitiva."
                    }
                },
                "required": ["torneo", "confirmar"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "asignar_cuota_personalizada",
            "description": "Asigna una cuota fija manual a un jugador específico (ej. medio torneo o becado) y rebalancea el resto.",
            "parameters": {
                "type": "object",
                "properties": {
                    "torneo": {
                        "type": "string",
                        "description": "Nombre o ID del torneo."
                    },
                    "jugador": {
                        "type": "string",
                        "description": "Nombre del jugador."
                    },
                    "cuota": {
                        "type": "number",
                        "description": "Monto fijo que deberá pagar este jugador."
                    }
                },
                "required": ["torneo", "jugador", "cuota"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "dar_de_baja_jugador",
            "description": "Da de baja a un jugador por lesión o abandono del torneo. Congela su cuota en lo que ya pagó y redistribuye el saldo restante entre los jugadores activos restantes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "torneo": {
                        "type": "string",
                        "description": "Nombre o ID del torneo."
                    },
                    "jugador": {
                        "type": "string",
                        "description": "Nombre del jugador que se da de baja."
                    },
                    "motivo": {
                        "type": "string",
                        "description": "Motivo de la baja (ej. 'lesión', 'cambio de ciudad'). Por defecto 'lesion'."
                    }
                },
                "required": ["torneo", "jugador"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "registrar_pago",
            "description": "Registra un abono o pago de un jugador para un torneo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "torneo": {
                        "type": "string",
                        "description": "Nombre o ID del torneo."
                    },
                    "jugador": {
                        "type": "string",
                        "description": "Nombre del jugador que paga."
                    },
                    "monto": {
                        "type": "number",
                        "description": "Monto abonado en pesos MXN."
                    },
                    "metodo_pago": {
                        "type": "string",
                        "description": "Método de pago: 'transferencia', 'efectivo', 'otro'."
                    },
                    "notas": {
                        "type": "string",
                        "description": "Notas opcionales (ej. 'anticipo', 'pago completo')."
                    },
                    "fecha": {
                        "type": "string",
                        "description": "Fecha opcional en formato YYYY-MM-DD si es un pago pasado."
                    },
                    "crear_nuevo_jugador": {
                        "type": "boolean",
                        "description": "True solo si el usuario confirmó explícitamente que desea crear/inscribir a esta persona como un jugador nuevo a pesar de no existir o diferir de una sugerencia."
                    }
                },
                "required": ["torneo", "jugador", "monto"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "modificar_total_pagado_jugador",
            "description": "Modifica o corrige el total que ha pagado un jugador en un torneo (ej. si hubo una equivocación en el abono anterior, o se desea corregir la suma total pagada directamente a un monto específico).",
            "parameters": {
                "type": "object",
                "properties": {
                    "torneo": {
                        "type": "string",
                        "description": "Nombre o ID del torneo."
                    },
                    "jugador": {
                        "type": "string",
                        "description": "Nombre del jugador cuyo total pagado se desea modificar o corregir."
                    },
                    "nuevo_total_pagado": {
                        "type": "number",
                        "description": "Monto total correcto que el jugador debe tener registrado como pagado (ej. 300, 500, o 0 si no ha pagado nada)."
                    },
                    "notas": {
                        "type": "string",
                        "description": "Motivo opcional del ajuste o corrección (ej. 'error en monto previo', 'acuerdo')."
                    }
                },
                "required": ["torneo", "jugador", "nuevo_total_pagado"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "eliminar_ultimo_pago_jugador",
            "description": "Elimina o cancela el último pago/abono registrado de un jugador en un torneo (útil si se registró un pago por error y se quiere borrar).",
            "parameters": {
                "type": "object",
                "properties": {
                    "torneo": {
                        "type": "string",
                        "description": "Nombre o ID del torneo."
                    },
                    "jugador": {
                        "type": "string",
                        "description": "Nombre del jugador al que se le desea eliminar su último abono."
                    }
                },
                "required": ["torneo", "jugador"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "registrar_partido",
            "description": "Registra el resultado de un partido de basketball (marcador, rival, tipo de partido).",
            "parameters": {
                "type": "object",
                "properties": {
                    "torneo": {
                        "type": "string",
                        "description": "Nombre o ID del torneo."
                    },
                    "rival": {
                        "type": "string",
                        "description": "Nombre del equipo rival (ej. 'Lobos', 'Bulls')."
                    },
                    "puntos_favor": {
                        "type": "integer",
                        "description": "Puntos anotados por nuestro equipo."
                    },
                    "puntos_contra": {
                        "type": "integer",
                        "description": "Puntos anotados por el rival."
                    },
                    "tipo_partido": {
                        "type": "string",
                        "description": "Tipo de partido: 'jornada', 'cuartos', 'semifinal', 'final', 'amistoso'."
                    },
                    "notas": {
                        "type": "string",
                        "description": "Notas opcionales del partido (ej. 'Tiempo extra', 'Buen partido de Memo')."
                    },
                    "fecha": {
                        "type": "string",
                        "description": "Fecha opcional en formato YYYY-MM-DD si fue un partido anterior."
                    }
                },
                "required": ["torneo", "rival", "puntos_favor", "puntos_contra"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "actualizar_resultado_torneo",
            "description": "Actualiza la posición en playoffs (seed), el resultado final del torneo o su estado.",
            "parameters": {
                "type": "object",
                "properties": {
                    "torneo": {
                        "type": "string",
                        "description": "Nombre o ID del torneo."
                    },
                    "lugar_playoffs": {
                        "type": "integer",
                        "description": "Posición / Seed en que clasificó el equipo a playoffs (ej. 1, 2, 3)."
                    },
                    "resultado_final": {
                        "type": "string",
                        "description": "Resultado alcanzado (ej. 'Campeón', 'Subcampeón', 'Semifinales', 'Fase Regular')."
                    },
                    "estado": {
                        "type": "string",
                        "description": "'active', 'completed', 'archived'."
                    }
                },
                "required": ["torneo"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_estado_torneo",
            "description": "Consulta el reporte completo de un torneo: finanzas (recaudado vs faltante), desglose por jugador con adeudos y récord de partidos (G-P).",
            "parameters": {
                "type": "object",
                "properties": {
                    "torneo": {
                        "type": "string",
                        "description": "Nombre o ID del torneo a consultar. Si se omite, consulta el torneo activo más reciente."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_saldo_jugador",
            "description": "Consulta cuánto ha pagado y cuánto debe un jugador en todos sus torneos activos o en uno específico.",
            "parameters": {
                "type": "object",
                "properties": {
                    "jugador": {
                        "type": "string",
                        "description": "Nombre del jugador a consultar."
                    }
                },
                "required": ["jugador"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "listar_torneos",
            "description": "Lista todos los torneos registrados y su estado actual.",
            "parameters": {
                "type": "object",
                "properties": {
                    "solo_activos": {
                        "type": "boolean",
                        "description": "Si es True solo lista los torneos en curso."
                    }
                }
            }
        }
    }
]

# ==========================================
# CORE AI PROCESSING LOGIC
# ==========================================

def clean_and_trim_messages(messages: list, max_turns: int = 6) -> list:
    """Safely cleans and trims conversation history to ensure valid OpenAI message sequences."""
    if not messages:
        return []
    system_msg = messages[0] if (isinstance(messages[0], dict) and messages[0].get("role") == "system") else {"role": "system", "content": ""}
    
    # Group history into atomic interaction turns starting at user messages
    turns = []
    current_turn = []
    for m in messages[1:]:
        role = getattr(m, "role", None) or (m.get("role") if isinstance(m, dict) else None)
        if role == "user" and current_turn:
            turns.append(current_turn)
            current_turn = [m]
        else:
            current_turn.append(m)
    if current_turn:
        turns.append(current_turn)
        
    # Keep only the last `max_turns` complete turns
    kept_turns = turns[-max_turns:] if len(turns) > max_turns else turns
    flattened = [system_msg]
    for turn in kept_turns:
        flattened.extend(turn)
    return flattened


async def run_basket_ai(chat_id: int, user_text: str) -> str:
    """Sends user text to GPT-4o-mini with basketball management tools."""
    cdmx_tz = ZoneInfo("America/Mexico_City")
    current_date = datetime.now(cdmx_tz).strftime('%Y-%m-%d %H:%M:%S')

    system_prompt = {
        "role": "system",
        "content": (
            f"Eres el Asistente Inteligente de Basketball y Gestión de Torneos. Fecha y hora actual en México: {current_date}. "
            "Tu objetivo es ayudar al usuario a administrar sus equipos de basketball: controlar los costos de los torneos, "
            "dividir equitativamente las cuotas entre los jugadores, registrar pagos/abonos, gestionar bajas por lesión recalculando saldos, "
            "y llevar el récord deportivo de partidos (victorias/derrotas/playoffs).\n\n"
            "REGLAS CLAVE:\n"
            "1. Responde SIEMPRE en español con tono amable, claro, entusiasta y deportivo (usa emojis como 🏀, 🏆, 💰, ✅, ⏳, ❌, 🏥).\n"
            "2. Formatea las cifras de dinero claramente con signo de pesos (ej. $1,200.00 MXN).\n"
            "3. MODIFICAR COSTOS VS CREAR: Si el usuario menciona una cantidad o cambio de costo para un torneo (ej. 'el costo de ledom es 8000', 'el total de ledom es 12000', 'cambia el costo a 9000'), NUNCA llames a crear_torneo. Llama SIEMPRE a actualizar_costo_torneo.\n"
            "4. CREACIÓN SEGURA: Cuando te pidan crear un torneo, si no mencionan el costo, pregúntalo. Si el nombre se parece a uno ya existente, advierte al usuario antes de duplicar.\n"
            "5. Si el usuario te da una lista de nombres (ej. 'Agrega a Juan #23 y Carlos #7'), llama a agregar_jugadores.\n"
            "6. Si te mencionan varios pagos en una misma frase (ej. 'Juan pagó $500 y Memo $600'), puedes llamar a registrar_pago para cada uno.\n"
            "7. Cuando consulten el estado de un torneo, presenta un resumen visual y ordenado con: Total Meta, Recaudado, Faltante, y el desglose de cada jugador (incluyendo su número de jersey si lo tiene, quién ya pagó al 100% y quién debe aún), más el récord de partidos si existen.\n"
            "8. Si un jugador se lesiona o sale, usa dar_de_baja_jugador y explica claramente al usuario cómo se congeló su saldo pagado y cómo se redistribuyó la diferencia entre los demás.\n"
            "9. Puedes asignar o actualizar números de camiseta/jersey ('Ponle el #23 a Omar' o al inscribir 'Agrega a Omar #23').\n"
            "10. Si el usuario pide eliminar un torneo, antes de eliminar pide confirmación explícita o llama a eliminar_torneo con confirmar=true si el usuario ya lo confirmó claramente.\n"
            "11. REGLA ESTRICTA DE JUGADORES Y PAGOS: NUNCA crees un jugador nuevo automáticamente sin preguntar. Si el usuario escribe un nombre no exacto o abreviado (ej. 'Saul' en vez de 'Saúl Morales', o 'Chuy' cuando hay varios Chuys), registrar_pago buscará nombres similares y devolverá una advertencia o sugerencia. Pregúntale SIEMPRE al usuario para confirmar si se refiere a ese jugador sugerido antes de aplicar el pago. Solo si el usuario confirma explícitamente que es un jugador nuevo y separado debes activar crear_nuevo_jugador=true.\n"
            "12. CORREGIR / EDITAR PAGOS DE JUGADORES: Si el usuario indica que se equivocó en lo que escribió de un pago, que desea modificar el total pagado de un jugador, o corregir un monto (ej. 'me equivoqué, Saúl pagó $300', 'modifica lo que ha pagado Saúl a $400', 'el total pagado de Saúl es $300', 'corrige el pago de Saúl'), utiliza SIEMPRE modificar_total_pagado_jugador. Si el usuario pide explícitamente borrar o cancelar el último pago, utiliza eliminar_ultimo_pago_jugador."
        )
    }

    if chat_id not in basket_sessions or not basket_sessions[chat_id]:
        basket_sessions[chat_id] = [system_prompt]
    else:
        basket_sessions[chat_id][0] = system_prompt

    basket_sessions[chat_id].append({"role": "user", "content": user_text})
    basket_sessions[chat_id] = clean_and_trim_messages(basket_sessions[chat_id], max_turns=6)

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=basket_sessions[chat_id],
            tools=basket_tools,
            tool_choice="auto"
        )
    except Exception as e:
        logger.warning(f"Error during initial OpenAI call (attempting clean reset): {e}")
        basket_sessions[chat_id] = [system_prompt, {"role": "user", "content": user_text}]
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=basket_sessions[chat_id],
            tools=basket_tools,
            tool_choice="auto"
        )

    message = response.choices[0].message
    if message.tool_calls:
        basket_sessions[chat_id].append(message)
        for tool_call in message.tool_calls:
            fname = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            tool_content = ""

            try:
                if fname == "crear_torneo":
                    nombre = args["nombre"]
                    forzar = args.get("forzar_creacion", False)
                    similar = database.find_similar_tournaments(nombre)
                    if similar and not forzar:
                        sim_names = ", ".join([f"'{s.name}' (ID: {s.id}, Costo: ${s.total_cost:.2f})" for s in similar])
                        tool_content = (
                            f"⚠️ ATENCIÓN: Ya existe un torneo activo con nombre similar: {sim_names}.\n"
                            f"NO se creó un torneo nuevo para evitar duplicados accidentales.\n"
                            f"Informa al usuario que ya existe ese torneo y pregúntale si deseaba actualizar el costo de '{similar[0].name}' "
                            f"o si realmente desea crear uno nuevo y separado con el nombre '{nombre}'."
                        )
                    else:
                        t = database.add_tournament(
                            name=nombre,
                            team_name=args.get("equipo", "Mi Equipo"),
                            total_cost=args.get("costo_total", 0.0),
                            registration_fee=args.get("inscripcion", 0.0),
                            referee_fee_total=args.get("arbitrajes_total", 0.0),
                            force_create=forzar
                        )
                        tool_content = f"🆕 Torneo '{t.name}' creado exitosamente: ID={t.id}, Equipo='{t.team_name}', CostoTotal=${t.total_cost:.2f} MXN."

                elif fname == "actualizar_costo_torneo":
                    success, msg, t = database.update_tournament_cost(
                        tournament_id_or_name=args["torneo"],
                        total_cost=args.get("costo_total"),
                        registration_fee=args.get("inscripcion"),
                        referee_fee_total=args.get("arbitrajes_total"),
                        team_name=args.get("equipo")
                    )
                    tool_content = msg if success else f"Error: {msg}"

                elif fname == "agregar_jugadores":
                    success, msg, t = database.add_players_to_tournament(args["torneo"], args["jugadores"])
                    if success and t:
                        rep = database.get_tournament_financial_report(t.id)
                        quota = rep["active_players"][0]["assigned_quota"] if rep and rep["active_players"] else 0.0
                        tool_content = f"{msg} Torneo '{t.name}'. Nueva cuota por jugador: ${quota:.2f} MXN. Total activos: {len(rep['active_players'])}."
                    else:
                        tool_content = f"Error: {msg}"

                elif fname == "asignar_cuota_personalizada":
                    success, msg = database.set_player_custom_quota(args["torneo"], args["jugador"], args["cuota"])
                    tool_content = msg if success else f"Error: {msg}"

                elif fname == "dar_de_baja_jugador":
                    success, msg, new_quota = database.drop_player_from_tournament(args["torneo"], args["jugador"], args.get("motivo", "lesion"))
                    if success:
                        tool_content = f"{msg} El saldo restante del torneo fue redistribuido. La nueva cuota para los jugadores activos es de ${new_quota:.2f} MXN."
                    else:
                        tool_content = f"Error: {msg}"

                elif fname == "registrar_pago":
                    success, msg, pdata = database.record_tournament_payment(
                        tournament_id_or_name=args["torneo"],
                        player_name=args["jugador"],
                        amount=args["monto"],
                        payment_method=args.get("metodo_pago", "efectivo"),
                        notes=args.get("notas") or args.get("notes"),
                        date_str=args.get("fecha"),
                        force_create_player=args.get("crear_nuevo_jugador", False)
                    )
                    if success and pdata:
                        status_str = "¡Totalmente pagado!" if pdata["is_paid_off"] else f"Resta pagar: ${pdata['remaining']:.2f}"
                        tool_content = f"Pago registrado: {pdata['player_name']} abonó ${pdata['amount_paid']:.2f} para '{pdata['tournament_name']}'. Total acumulado: ${pdata['total_paid']:.2f} de ${pdata['quota']:.2f}. {status_str}"
                    else:
                        tool_content = msg

                elif fname == "modificar_total_pagado_jugador":
                    success, msg, adata = database.adjust_player_total_paid(
                        tournament_id_or_name=args["torneo"],
                        player_name=args["jugador"],
                        new_total_paid=args["nuevo_total_pagado"],
                        notes=args.get("notas")
                    )
                    if success and adata:
                        status_str = "¡Totalmente saldado!" if adata["is_paid_off"] else f"Resta pagar: ${adata['remaining']:.2f} MXN"
                        tool_content = (
                            f"✅ Total pagado corregido para {adata['player_name']} en '{adata['tournament_name']}': "
                            f"cambió de ${adata['previous_total']:.2f} a ${adata['new_total_paid']:.2f} MXN. "
                            f"Cuota asignada: ${adata['quota']:.2f} MXN. {status_str}"
                        )
                    else:
                        tool_content = msg

                elif fname == "eliminar_ultimo_pago_jugador":
                    success, msg, ddata = database.delete_last_player_payment(
                        tournament_id_or_name=args["torneo"],
                        player_name=args["jugador"]
                    )
                    if success and ddata:
                        status_str = "¡Totalmente saldado!" if ddata["is_paid_off"] else f"Resta pagar: ${ddata['remaining']:.2f} MXN"
                        tool_content = (
                            f"🗑️ Se eliminó el último pago de ${ddata['deleted_amount']:.2f} MXN de {ddata['player_name']} en '{ddata['tournament_name']}'. "
                            f"Nuevo total pagado: ${ddata['new_total_paid']:.2f} MXN. {status_str}"
                        )
                    else:
                        tool_content = msg

                elif fname == "registrar_partido":
                    success, msg, mdata = database.record_tournament_match(
                        tournament_id_or_name=args["torneo"],
                        opponent=args["rival"],
                        team_score=args["puntos_favor"],
                        opponent_score=args["puntos_contra"],
                        match_type=args.get("tipo_partido", "jornada"),
                        notes=args.get("notas"),
                        date_str=args.get("fecha")
                    )
                    if success and mdata:
                        res = "Victoria" if mdata["is_win"] else "Derrota"
                        tool_content = f"Partido registrado: {res} vs {mdata['opponent']} ({mdata['score']}). Récord del torneo: {mdata['record']}."
                    else:
                        tool_content = f"Error: {msg}"

                elif fname == "actualizar_resultado_torneo":
                    t = database.update_tournament_result(
                        tournament_id_or_name=args["torneo"],
                        playoff_seed=args.get("lugar_playoffs"),
                        final_result=args.get("resultado_final"),
                        status=args.get("estado")
                    )
                    if t:
                        tool_content = f"Torneo '{t.name}' actualizado: Seed={t.playoff_seed}, Resultado='{t.final_result}', Estado='{t.status}'."
                    else:
                        tool_content = "Torneo no encontrado."

                elif fname == "consultar_estado_torneo":
                    tourn_query = args.get("torneo")
                    if not tourn_query:
                        active = database.get_active_tournaments()
                        if active:
                            tourn_query = active[0].id
                        else:
                            all_t = database.get_all_tournaments()
                            if all_t:
                                tourn_query = all_t[0].id

                    if not tourn_query:
                        tool_content = "No hay torneos registrados actualmente."
                    else:
                        rep = database.get_tournament_financial_report(tourn_query)
                        if not rep:
                            tool_content = "Torneo no encontrado."
                        else:
                            tool_content = json.dumps(rep, ensure_ascii=False)

                elif fname == "consultar_saldo_jugador":
                    psummary = database.get_player_summary(args["jugador"])
                    if not psummary:
                        tool_content = f"No se encontró al jugador '{args['jugador']}' o no tiene torneos registrados."
                    else:
                        tool_content = json.dumps(psummary, ensure_ascii=False)

                elif fname == "asignar_numero_jugador":
                    success, msg = database.set_player_jersey_number(
                        player_name=args["jugador"],
                        jersey_number=args["numero"],
                        tournament_id_or_name=args.get("torneo")
                    )
                    tool_content = msg if success else f"Error: {msg}"

                elif fname == "eliminar_torneo":
                    if not args.get("confirmar", False):
                        tool_content = "Acción cancelada. Para eliminar el torneo se requiere confirmación explícita."
                    else:
                        success, msg, summary = database.delete_tournament(args["torneo"])
                        if success:
                            tool_content = msg
                        else:
                            tool_content = f"Error: {msg}"

                elif fname == "listar_torneos":
                    only_act = args.get("solo_activos", True)
                    tourns = database.get_active_tournaments() if only_act else database.get_all_tournaments()
                    if not tourns:
                        tool_content = "No hay torneos registrados."
                    else:
                        lines = [f"- [ID: {t.id}] {t.name} (Equipo: {t.team_name}, Costo: ${t.total_cost:.2f}, Estado: {t.status})" for t in tourns]
                        tool_content = f"Torneos encontrados ({len(tourns)}):\n" + "\n".join(lines)

            except Exception as e:
                logger.exception(f"Error executing basket tool {fname}:")
                tool_content = f"Error al ejecutar la acción: {str(e)}"

            basket_sessions[chat_id].append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": fname,
                "content": tool_content
            })

        final_response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=basket_sessions[chat_id]
        )
        reply_text = final_response.choices[0].message.content
        basket_sessions[chat_id].append(final_response.choices[0].message)
        return reply_text
    else:
        basket_sessions[chat_id].append(message)
        return message.content or "No pude entender tu solicitud. Por favor intenta ser más específico."


# ==========================================
# TELEGRAM MESSAGE HANDLERS
# ==========================================

async def basket_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /start command in BasketBot."""
    user = update.effective_user

    if not is_basket_user_authorized(user.id):
        logger.warning(f"Unauthorized BasketBot access by user {user.id} ({user.username}).")
        await update.message.reply_text(
            f"⛔ Lo siento, no estás en la lista de administradores autorizados de BasketBot.\n\n"
            f"Tu ID de Telegram es: `{user.id}`\n\n"
            f"Pídele al administrador principal que agregue tu ID a la variable `BASKET_ALLOWED_USER_IDS` en Railway."
        )
        return

    await update.message.reply_html(
        rf"🏀 ¡Hola {user.mention_html()}! Soy tu **Basket Tracker Bot**." + "\n\n"
        "Te ayudaré a administrar las finanzas y el récord de tus equipos de basketball:\n\n"
        "🏆 **Torneos:** *'Crea el torneo Ledom de $12,000 para Monarque'*\n"
        "👥 **Jugadores:** *'Agrega a Juan, Carlos, Memo y Pedro al torneo Ledom'*\n"
        "💰 **Pagos:** *'Juan pagó $1,200 por transferencia'* o *'Memo dio $500 en efectivo'*\n"
        "📊 **Estado:** *'¿Cómo van los pagos del torneo?'* o *'¿Cuánto debe Carlos?'*\n"
        "🏥 **Bajas:** *'Memo se lesionó, dalo de baja del torneo'*\n"
        "🏀 **Partidos:** *'Ganamos 64-58 contra Lobos en la jornada 3'*\n\n"
        "🎙 *¡También puedes enviarme notas de voz con cualquier reporte o pago!*"
    )

async def process_basket_text(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str, processing_msg):
    """Processes user text and handles layered Telegram message editing."""
    chat_id = update.effective_chat.id
    try:
        reply_text = await run_basket_ai(chat_id, user_text)
        
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=processing_msg.message_id,
                text=reply_text,
                parse_mode="Markdown"
            )
        except Exception:
            try:
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=processing_msg.message_id,
                    text=reply_text
                )
            except Exception as e:
                logger.error(f"Failed to edit message in basket bot: {e}. Sending new message.")
                await context.bot.send_message(chat_id=chat_id, text=reply_text)

    except Exception as e:
        logger.exception("Error in process_basket_text:")
        err_msg = str(e)
        if "AuthenticationError" in type(e).__name__ or "api_key" in err_msg.lower():
            user_error = "⚠️ **Error de configuración**: La clave de acceso con el servicio de IA no es válida. Por favor repórtalo con el administrador."
        elif "RateLimitError" in type(e).__name__ or "quota" in err_msg.lower():
            user_error = "⚠️ **Error de servicio**: El servicio de IA está temporalmente saturado o sin cuota disponible. Por favor repórtalo con el administrador."
        else:
            user_error = "⚠️ Ocurrió un error al procesar tu solicitud. Por favor intenta de nuevo. Si el problema persiste, repórtalo con el administrador."

        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=processing_msg.message_id,
                text=user_error,
                parse_mode="Markdown"
            )
        except Exception:
            await context.bot.send_message(chat_id=chat_id, text=user_error)

async def handle_basket_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes incoming text message for BasketBot."""
    user = update.effective_user

    if not is_basket_user_authorized(user.id):
        logger.warning(f"Unauthorized BasketBot access by user {user.id} ({user.username}).")
        await update.message.reply_text(
            f"⛔ Lo siento, no estás en la lista de administradores autorizados de BasketBot.\n\n"
            f"Tu ID de Telegram es: `{user.id}`\n\n"
            f"Pídele al administrador principal que agregue tu ID a la variable `BASKET_ALLOWED_USER_IDS` en Railway."
        )
        return

    user_text = update.message.text
    processing_msg = await update.message.reply_text("⏳ Procesando...")
    await process_basket_text(update, context, user_text, processing_msg)

async def handle_basket_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes incoming voice notes using OpenAI Whisper for BasketBot."""
    user = update.effective_user

    if not is_basket_user_authorized(user.id):
        logger.warning(f"Unauthorized BasketBot access by user {user.id} ({user.username}).")
        await update.message.reply_text(
            f"⛔ Lo siento, no estás en la lista de administradores autorizados de BasketBot.\n\n"
            f"Tu ID de Telegram es: `{user.id}`\n\n"
            f"Pídele al administrador principal que agregue tu ID a la variable `BASKET_ALLOWED_USER_IDS` en Railway."
        )
        return

    voice_obj = update.message.voice or update.message.audio
    if not voice_obj:
        await update.message.reply_text("⚠️ No se pudo leer el archivo de audio recibido.")
        return

    status_msg = await update.message.reply_text("🎙 Transcribiendo nota de voz...")

    try:
        tg_file = await voice_obj.get_file()
        file_bytes = await tg_file.download_as_bytearray()

        audio_stream = io.BytesIO(file_bytes)
        audio_stream.name = "voice.ogg"

        transcription = await client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_stream
        )

        user_text = transcription.text.strip()
        if not user_text:
            await status_msg.edit_text("🎙 No se detectó ninguna voz comprensible en la nota de audio.")
            return

        try:
            await status_msg.edit_text(f"🎙 *Transcripción:* \"{user_text}\"\n\n⏳ Procesando...", parse_mode="Markdown")
        except Exception:
            await status_msg.edit_text(f"🎙 Transcripción: \"{user_text}\"\n\n⏳ Procesando...")

        await process_basket_text(update, context, user_text, status_msg)

    except Exception as e:
        logger.exception("Error transcribing voice note in BasketBot:")
        await status_msg.edit_text(f"⚠️ Ocurrió un error al transcribir tu nota de voz: {str(e)}\nPor favor intenta de nuevo.")


# ==========================================
# BOT LIFECYCLE MANAGEMENT
# ==========================================

basket_app = None

async def start_basket_bot():
    """Initializes and starts BasketBot polling in the background."""
    global basket_app
    token = os.getenv("BASKET_BOT_TOKEN")

    if not token or token == "your_basket_bot_token_here":
        logger.info("BASKET_BOT_TOKEN is not configured. BasketBot will be inactive.")
        return

    try:
        basket_app = ApplicationBuilder().token(token).build()

        basket_app.add_handler(CommandHandler("start", basket_start))
        basket_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_basket_message))
        basket_app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_basket_voice))

        await basket_app.initialize()
        await basket_app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        await basket_app.start()

        logger.info("🏀 Basket Tracker Telegram Bot successfully started in the background.")

    except Exception as e:
        logger.error(f"Failed to start BasketBot background task: {e}")

async def stop_basket_bot():
    """Stops BasketBot gracefully."""
    global basket_app
    if basket_app:
        try:
            await basket_app.updater.stop()
            await basket_app.stop()
            await basket_app.shutdown()
            logger.info("BasketBot shut down gracefully.")
        except Exception as e:
            logger.error(f"Error during BasketBot shutdown: {e}")
