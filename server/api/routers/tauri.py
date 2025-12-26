from fastapi import APIRouter, HTTPException, Depends
from server.api.deps import get_state
from server.core.state import AppState


router = APIRouter()


@router.get("/tauri/commands")
async def get_tauri_commands(state: AppState = Depends(get_state)):
    """
    Get available Tauri commands

    Returns:
        Dictionary with Tauri commands
    """
    try:
        commands = state.tauri_integration.get_all_commands()
        return {"status": "success", "commands": commands}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tauri/commands/{command_name}")
async def get_tauri_command(command_name: str, state: AppState = Depends(get_state)):
    """
    Get details for a specific Tauri command

    Args:
        command_name: Name of the command

    Returns:
        Dictionary with command details
    """
    try:
        command = state.tauri_integration.get_command(command_name)
        if command:
            return {"status": "success", "command": command}
        else:
            raise HTTPException(status_code=404, detail="Command not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tauri/rust-skeleton")
async def get_rust_skeleton(state: AppState = Depends(get_state)):
    """
    Get Rust skeleton code for Tauri integration

    Returns:
        Dictionary with Rust skeleton code
    """
    try:
        skeleton = state.tauri_integration.generate_rust_skeleton()
        return {"status": "success", "skeleton": skeleton}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tauri/frontend-hooks")
async def get_frontend_hooks(state: AppState = Depends(get_state)):
    """
    Get frontend hooks for Tauri integration

    Returns:
        Dictionary with frontend hooks code
    """
    try:
        hooks = state.tauri_integration.generate_frontend_hooks()
        return {"status": "success", "hooks": hooks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tauri/config")
async def get_tauri_config(state: AppState = Depends(get_state)):
    """
    Get Tauri configuration

    Returns:
        Dictionary with Tauri configuration
    """
    try:
        config = state.tauri_integration.generate_tauri_config()
        return {"status": "success", "config": config}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tauri/security")
async def get_security_recommendations(state: AppState = Depends(get_state)):
    """
    Get security recommendations for Tauri integration

    Returns:
        Dictionary with security recommendations
    """
    try:
        recommendations = state.tauri_integration.get_security_recommendations()
        return {"status": "success", "recommendations": recommendations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tauri/performance")
async def get_performance_tips(state: AppState = Depends(get_state)):
    """
    Get performance tips for Tauri integration

    Returns:
        Dictionary with performance tips
    """
    try:
        tips = state.tauri_integration.get_performance_tips()
        return {"status": "success", "tips": tips}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tauri/checklist")
async def get_integration_checklist(state: AppState = Depends(get_state)):
    """
    Get integration checklist for Tauri

    Returns:
        Dictionary with integration checklist
    """
    try:
        checklist = state.tauri_integration.get_integration_checklist()
        return {"status": "success", "checklist": checklist}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tauri/setup-guide")
async def get_setup_guide():
    """
    Get Tauri setup guide

    Returns:
        Dictionary with setup guide
    """
    try:
        from src.tauri_integration import get_tauri_setup_guide

        guide = get_tauri_setup_guide()
        return {"status": "success", "guide": guide}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
