"""
FastAPI Web Application for LoanPilot.
Main entry point with routing, middleware, and static file serving.
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Request, Form, File, UploadFile, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import ValidationError

# Add parent directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

# Import from current directory
try:
    from . import models, query_engine, parsers, text_formatter, program_uploader, database_manager
except ImportError:
    # Fallback for direct execution
    import models
    import query_engine
    import parsers
    import text_formatter
    import program_uploader
    import database_manager


# Configure logging
log_dir = Path(__file__).parent / "logs"
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_dir / 'loanpilot.log')
    ]
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="LoanPilot API",
    description="AI-powered loan program matching system with natural language query support",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Add middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info("🚀 Starting LoanPilot FastAPI application...")
    try:
        engine = query_engine.get_query_engine()
        logger.info("✓ Query engine initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize query engine: {e}")
        raise


# Health check endpoint
@app.get("/api/health", response_model=models.HealthResponse)
async def health_check():
    """
    Check API and query engine health.
    Essential logging: service health status.
    """
    try:
        engine = query_engine.get_query_engine()
        health_status = engine.check_health()

        logger.info(f"Health check: available={health_status['available']}")

        return models.HealthResponse(
            success=True,
            timestamp=datetime.utcnow().isoformat(),
            **health_status
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return models.HealthResponse(
            success=False,
            available=False,
            error=str(e),
            timestamp=datetime.utcnow().isoformat()
        )


# Query execution endpoint
@app.post("/api/query/execute")
async def execute_query(
    request: Request,
    query: str = Form(...),
    selectedPrograms: Optional[str] = Form(None),
    programContext: Optional[str] = Form(None)
):
    """
    Execute a natural language query against loan program database.
    Essential logging: query received, parameters extracted, execution result.
    """
    try:
        # Log query request
        logger.info(f"🔍 Query request: {query}")

        if programContext:
            logger.info(f"📌 Program context: {programContext}")

        # Parse selected programs for context
        context_params = {}
        if selectedPrograms:
            try:
                programs = json.loads(selectedPrograms)
                if programs:
                    context_params['selected_programs'] = [p['programName'] for p in programs]
                    context_params['selected_servicers'] = list(set(p['servicer'] for p in programs))
                    logger.info(f"📝 Context parameters: {context_params}")
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ Could not parse selected programs: {e}")

        # Execute query through engine
        engine = query_engine.get_query_engine()
        result = engine.execute_query(query, context_params)

        logger.info(f"✅ Query completed: success={result['success']}")

        # Parse results to determine type and generate appropriate response
        parsed_response = await parsers.parse_query_results(result['results'], query)

        # Check if this is an HTMX request
        is_htmx = request.headers.get('hx-request') == 'true'

        if is_htmx:
            # Generate chat message for left panel
            context_info = f'<div class="text-[10px] opacity-50 mt-1.5 italic">Context: {parsers.escape_html(programContext)}</div>' \
                if programContext else ''

            chat_message = f'''
        <div class="chat chat-end mb-2">
          <div class="chat-bubble chat-bubble-primary text-xs">
            <div>{parsers.escape_html(result['query'])}</div>
            {context_info}
          </div>
        </div>
        <div class="chat chat-start">
          <div class="chat-bubble bg-base-200 text-base-content text-sm">
            {parsed_response['summary']}
          </div>
        </div>
      '''

            # Generate structured results for right panel with OOB swap
            results_panel = f'''
        <div hx-swap-oob="innerHTML:#resultsContent">
          {parsed_response['structuredData']}
        </div>
        <div hx-swap-oob="innerHTML:#resultsHeader">
          {parsed_response['header']}
        </div>
      '''

            # Add auto-selection trigger if single program query
            if parsed_response.get('autoSelectProgram'):
                program_info = parsed_response['autoSelectProgram']
                program_name = parsers.escape_html(program_info['programName']).replace("'", "\\'")
                servicer = parsers.escape_html(program_info['servicer']).replace("'", "\\'")

                results_panel += f'''
          <script>
            // Auto-select the program for single-program queries
            if (window.appFunctions && window.appFunctions.toggleProgramSelection) {{
              setTimeout(() => {{
                window.appFunctions.clearProgramSelection();
                window.appFunctions.toggleProgramSelection('{program_name}', '{servicer}');
                console.log('🎯 Auto-selected program: {program_name} ({servicer})');
              }}, 100);
            }}
          </script>
        '''

            return HTMLResponse(content=chat_message + results_panel)

        # JSON response for non-HTMX requests
        return JSONResponse(content=result)

    except ValidationError as e:
        logger.error(f"❌ Validation error: {e}")
        if request.headers.get('hx-request') == 'true':
            return HTMLResponse(
                content=f'''
          <div class="alert alert-error shadow-sm mb-3">
            <span>Validation error: {parsers.escape_html(str(e))}</span>
          </div>
        ''',
                status_code=400
            )
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error(f"❌ Query execution error: {e}", exc_info=True)

        if request.headers.get('hx-request') == 'true':
            return HTMLResponse(
                content=f'''
          <div class="alert alert-error shadow-sm mb-3">
            <div>
              <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current flex-shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>Query failed: {parsers.escape_html(str(e))}</span>
            </div>
          </div>
        ''',
                status_code=500
            )

        raise HTTPException(status_code=500, detail=str(e))


# Get program parameter detail endpoint
@app.get("/api/program/parameter")
async def get_program_parameter(
    programName: str,
    servicer: str,
    paramType: str
):
    """
    Get specific parameter detail for a program.
    """
    try:
        engine = query_engine.get_query_engine()

        # Map paramType to database column
        param_map = {
            'occupancy': 'occupancy',
            'transaction': 'transaction_type',
            'reserves': 'reserves',
            'documentation': 'income_documentation',
            'citizenship': 'citizenship'
        }

        param_name = param_map.get(paramType)
        if not param_name:
            return JSONResponse(
                content={"error": f"Unknown parameter type: {paramType}"},
                status_code=400
            )

        value = engine.fetch_program_parameter(programName, servicer, param_name)

        # Format the value using Anthropic API to convert technical expressions to English
        if value and value != "Not specified":
            formatter = text_formatter.get_formatter()
            formatted_value = formatter.format_parameter_value(value, param_name, programName)
        else:
            formatted_value = "Not specified"

        return JSONResponse(content={
            "success": True,
            "programName": programName,
            "paramType": paramType,
            "value": formatted_value
        })

    except Exception as e:
        logger.error(f"❌ Error fetching parameter: {e}")
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )


# Get available scripts endpoint
@app.get("/api/query/scripts", response_model=models.ScriptsResponse)
async def get_scripts(request: Request):
    """
    Get list of available query scripts.
    Essential logging: number of scripts retrieved.
    """
    try:
        engine = query_engine.get_query_engine()
        scripts = engine.get_available_scripts()

        logger.info(f"✓ Retrieved {len(scripts)} scripts")

        # Check if this is an HTMX request
        if request.headers.get('hx-request') == 'true':
            scripts_html = []
            for script in scripts:
                scripts_html.append(f'''
        <div class="border border-base-300 rounded p-2 mb-2 hover:bg-base-50 cursor-pointer"
             onclick="document.querySelector('[name=query]').value='{parsers.escape_html(script['prompt'])}'; document.getElementById('queryForm').requestSubmit();">
          <div class="font-mono text-sm font-semibold">{parsers.escape_html(script['name'])}</div>
          <div class="text-xs text-base-content/60">{parsers.escape_html(script['description'])}</div>
          <div class="text-xs text-base-content/40 mt-1">
            <span class="badge badge-xs badge-ghost">{parsers.escape_html(script['prompt'])}</span>
          </div>
        </div>
      ''')

            html_content = f'''
        <div class="space-y-2">
          <div class="text-sm font-semibold mb-2">Available Scripts ({len(scripts)}):</div>
          {''.join(scripts_html) if scripts_html else '<div class="text-xs text-base-content/60">No scripts found</div>'}
        </div>
      '''

            return HTMLResponse(content=html_content)

        # JSON response
        return models.ScriptsResponse(
            success=True,
            scripts=[models.ScriptInfo(**s) for s in scripts]
        )

    except Exception as e:
        logger.error(f"❌ Error fetching scripts: {e}", exc_info=True)

        if request.headers.get('hx-request') == 'true':
            return HTMLResponse(
                content=f'''
          <div class="alert alert-warning">
            <span>Could not load scripts: {parsers.escape_html(str(e))}</span>
          </div>
        ''',
                status_code=500
            )

        raise HTTPException(status_code=500, detail=str(e))


# ========== DATABASE MANAGEMENT ENDPOINTS ==========

@app.get("/api/database/info")
async def get_database_info():
    """Get current database information (tables, programs, size)"""
    try:
        manager = database_manager.DatabaseManager()
        info = manager.get_database_info()

        return JSONResponse(content={
            "success": True,
            "database": info
        })

    except Exception as e:
        logger.error(f"❌ Error getting database info: {e}")
        return JSONResponse(
            content={"success": False, "error": str(e)},
            status_code=500
        )


@app.get("/api/database/backups")
async def list_database_backups():
    """List all available database backups"""
    try:
        manager = database_manager.DatabaseManager()
        backups = manager.list_backups()

        return JSONResponse(content={
            "success": True,
            "backups": backups,
            "count": len(backups)
        })

    except Exception as e:
        logger.error(f"❌ Error listing backups: {e}")
        return JSONResponse(
            content={"success": False, "error": str(e)},
            status_code=500
        )


@app.post("/api/database/backup")
async def create_database_backup():
    """Create a backup of the current database"""
    try:
        logger.info("📦 Creating database backup...")

        manager = database_manager.DatabaseManager()
        result = manager.create_backup()

        if result["success"]:
            logger.info(f"✅ Backup created: {result['backup_name']}")
        else:
            logger.error(f"❌ Backup failed: {result.get('error')}")

        return JSONResponse(content=result)

    except Exception as e:
        logger.error(f"❌ Backup error: {e}", exc_info=True)
        return JSONResponse(
            content={"success": False, "error": str(e)},
            status_code=500
        )


@app.post("/api/database/restore")
async def restore_database_backup(backup_name: str = Form(...)):
    """Restore database from a backup file"""
    try:
        logger.info(f"🔄 Restoring database from: {backup_name}")

        manager = database_manager.DatabaseManager()
        result = manager.restore_backup(backup_name)

        if result["success"]:
            logger.info(f"✅ Database restored from {backup_name}")
        else:
            logger.error(f"❌ Restore failed: {result.get('error')}")

        return JSONResponse(content=result)

    except Exception as e:
        logger.error(f"❌ Restore error: {e}", exc_info=True)
        return JSONResponse(
            content={"success": False, "error": str(e)},
            status_code=500
        )


@app.post("/api/database/reset")
async def reset_database(create_backup: bool = Form(True)):
    """
    Reset database: drop all tables and repopulate from TSV.
    Creates a backup by default before resetting.
    """
    try:
        logger.info("🔄 Database reset requested...")
        logger.info(f"   Create backup: {create_backup}")

        manager = database_manager.DatabaseManager()
        result = manager.reset_database(create_backup=create_backup)

        if result["success"]:
            logger.info("✅ Database reset completed successfully")
        else:
            logger.error(f"❌ Database reset failed: {result.get('error')}")

        return JSONResponse(content=result)

    except Exception as e:
        logger.error(f"❌ Reset error: {e}", exc_info=True)
        return JSONResponse(
            content={"success": False, "error": str(e)},
            status_code=500
        )


# ========== PROGRAM UPLOAD ENDPOINTS ==========

@app.get("/api/programs/servicers")
async def get_servicers():
    """Get list of available servicers (Prime, LoanStream)"""
    try:
        uploader = program_uploader.ProgramUploader()
        servicers = uploader.get_servicers()

        return JSONResponse(content={
            "success": True,
            "servicers": servicers
        })

    except Exception as e:
        logger.error(f"❌ Error fetching servicers: {e}")
        return JSONResponse(
            content={"success": False, "error": str(e)},
            status_code=500
        )


@app.post("/api/programs/validate")
async def validate_program_tsv(file: UploadFile = File(...)):
    """
    Validate uploaded TSV file for new program.
    Checks structure, row count, attribute matching, etc.
    """
    try:
        logger.info(f"📤 Validating TSV file: {file.filename}")

        # Read file content
        content = await file.read()

        # Validate
        uploader = program_uploader.ProgramUploader()
        result = uploader.validate_tsv(content, file.filename)

        logger.info(f"✅ Validation complete: valid={result.is_valid}, program={result.program_name}")

        return JSONResponse(content={
            "success": True,
            "validation": {
                "is_valid": result.is_valid,
                "errors": result.errors,
                "warnings": result.warnings,
                "program_name": result.program_name,
                "servicer": result.servicer,
                "row_count": result.row_count,
                "attributes_matched": result.attributes_matched
            }
        })

    except Exception as e:
        logger.error(f"❌ Validation error: {e}", exc_info=True)
        return JSONResponse(
            content={"success": False, "error": str(e)},
            status_code=500
        )


@app.post("/api/programs/import")
async def import_program(
    file: UploadFile = File(...),
    program_name: str = Form(...),
    servicer: str = Form(...)
):
    """
    Import validated TSV file into database.
    Adds new program column to appropriate table.
    """
    try:
        logger.info(f"📥 Importing program: {program_name} ({servicer})")

        # Read file content
        content = await file.read()

        # Validate first
        uploader = program_uploader.ProgramUploader()
        validation = uploader.validate_tsv(content, file.filename)

        if not validation.is_valid:
            logger.warning(f"⚠️ Import rejected - validation failed: {validation.errors}")
            return JSONResponse(
                content={
                    "success": False,
                    "error": "Validation failed",
                    "validation_errors": validation.errors
                },
                status_code=400
            )

        # Import
        import_result = uploader.import_program(content, program_name, servicer)

        if import_result["success"]:
            logger.info(f"✅ Program imported successfully: {program_name}")
        else:
            logger.error(f"❌ Import failed: {import_result.get('error')}")

        return JSONResponse(content=import_result)

    except Exception as e:
        logger.error(f"❌ Import error: {e}", exc_info=True)
        return JSONResponse(
            content={"success": False, "error": str(e)},
            status_code=500
        )


@app.get("/api/programs/count")
async def get_program_counts():
    """Get count of programs for each servicer"""
    try:
        uploader = program_uploader.ProgramUploader()

        prime_count = uploader.get_program_count("Prime")
        loanstream_count = uploader.get_program_count("LoanStream")

        return JSONResponse(content={
            "success": True,
            "counts": {
                "Prime": prime_count,
                "LoanStream": loanstream_count,
                "total": prime_count + loanstream_count
            }
        })

    except Exception as e:
        logger.error(f"❌ Error fetching program counts: {e}")
        return JSONResponse(
            content={"success": False, "error": str(e)},
            status_code=500
        )


# Serve static files (CSS, JS, images)
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# Serve index.html
@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the main HTML page."""
    index_path = static_dir / "index.html"
    if index_path.exists():
        return HTMLResponse(content=index_path.read_text())
    else:
        return HTMLResponse(content="<h1>LoanPilot Web - Index not found</h1>", status_code=404)


# Exception handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """Handle 404 errors."""
    logger.warning(f"404 Not Found: {request.url.path}")
    return JSONResponse(
        status_code=404,
        content={"success": False, "error": "Not found"}
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception):
    """Handle 500 errors."""
    logger.error(f"500 Internal Server Error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn

    # Create logs directory if it doesn't exist
    Path("web-app/logs").mkdir(parents=True, exist_ok=True)

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
