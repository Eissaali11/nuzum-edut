import os
import io
import logging

logger = logging.getLogger(__name__)

try:
    from replit.object_storage import Client
    client = Client()
    STORAGE_AVAILABLE = True
    logger.info("Replit Object Storage connected successfully")
except Exception as e:
    logger.warning(f"Object Storage not available: {e}")
    client = None
    STORAGE_AVAILABLE = False


def _get_storage_key(folder_name, filename):
    return f"{folder_name}/{filename}"


def _get_storage_key_from_path(local_path):
    if local_path.startswith('static/uploads/'):
        return local_path[len('static/uploads/'):]
    if local_path.startswith('/') and '/static/uploads/' in local_path:
        idx = local_path.index('/static/uploads/') + len('/static/uploads/')
        return local_path[idx:]
    return local_path


def sync_to_cloud(local_path):
    if not STORAGE_AVAILABLE or client is None:
        return False
    if not os.path.exists(local_path):
        return False
    try:
        storage_key = _get_storage_key_from_path(local_path)
        with open(local_path, 'rb') as f:
            file_bytes = f.read()
        client.upload_from_bytes(storage_key, file_bytes)
        logger.info(f"Synced to cloud: {storage_key}")
        return True
    except Exception as e:
        logger.warning(f"Failed to sync to cloud {local_path}: {e}")
        return False


def upload_image(file_data, folder_name, filename):
    if hasattr(file_data, 'read'):
        file_bytes = file_data.read()
    else:
        file_bytes = file_data

    local_path = os.path.join('static', 'uploads', folder_name, filename)
    os.makedirs(os.path.dirname(local_path), exist_ok=True)

    with open(local_path, 'wb') as f:
        f.write(file_bytes)

    if STORAGE_AVAILABLE and client is not None:
        try:
            storage_key = _get_storage_key(folder_name, filename)
            client.upload_from_bytes(storage_key, file_bytes)
            logger.info(f"Uploaded to cloud: {storage_key}")
        except Exception as e:
            logger.warning(f"Cloud upload failed for {folder_name}/{filename}: {e}")

    return f'static/uploads/{folder_name}/{filename}'


def download_image(object_key):
    if object_key.startswith('static/uploads/'):
        local_path = object_key
        storage_key = object_key[len('static/uploads/'):]
    elif object_key.startswith('uploads/'):
        local_path = os.path.join('static', object_key)
        storage_key = object_key[len('uploads/'):]
    else:
        local_path = os.path.join('static', 'uploads', object_key)
        storage_key = object_key

    if os.path.exists(local_path):
        try:
            with open(local_path, 'rb') as f:
                return f.read()
        except Exception as e:
            logger.warning(f"Error reading local file {local_path}: {e}")

    if STORAGE_AVAILABLE and client is not None:
        try:
            data = client.download_as_bytes(storage_key)
            if data:
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                with open(local_path, 'wb') as f:
                    f.write(data)
                logger.info(f"Restored from cloud: {storage_key}")
                return data
        except Exception as e:
            logger.debug(f"Cloud download failed for {storage_key}: {e}")

    return None


def delete_image(object_key):
    deleted_local = False
    deleted_cloud = False

    if object_key.startswith('static/uploads/'):
        local_path = object_key
        storage_key = object_key[len('static/uploads/'):]
    else:
        local_path = os.path.join('static', 'uploads', object_key)
        storage_key = object_key

    if os.path.exists(local_path):
        try:
            os.remove(local_path)
            deleted_local = True
        except Exception as e:
            logger.warning(f"Error deleting local file {local_path}: {e}")

    if STORAGE_AVAILABLE and client is not None:
        try:
            client.delete(storage_key)
            deleted_cloud = True
        except Exception as e:
            logger.debug(f"Cloud delete failed for {storage_key}: {e}")

    return deleted_local or deleted_cloud


def list_images(folder_name):
    results = set()

    local_path = os.path.join('static', 'uploads', folder_name)
    if os.path.exists(local_path):
        try:
            for f in os.listdir(local_path):
                if os.path.isfile(os.path.join(local_path, f)):
                    results.add(f"{folder_name}/{f}")
        except Exception as e:
            logger.warning(f"Error listing local images in {folder_name}: {e}")

    if STORAGE_AVAILABLE and client is not None:
        try:
            objects = client.list(prefix=f"{folder_name}/")
            for obj in objects:
                results.add(obj.name)
        except Exception as e:
            logger.debug(f"Error listing cloud images in {folder_name}: {e}")

    return list(results)


def migrate_existing_files():
    if not STORAGE_AVAILABLE or client is None:
        logger.warning("Object Storage not available — cannot migrate")
        return 0

    base_path = "static/uploads"
    migrated_count = 0

    if not os.path.exists(base_path):
        return 0

    for root_dir, dirs, files in os.walk(base_path):
        for filename in files:
            file_path = os.path.join(root_dir, filename)
            try:
                rel_path = os.path.relpath(file_path, base_path)
                storage_key = rel_path.replace('\\', '/')
                with open(file_path, 'rb') as f:
                    file_bytes = f.read()
                client.upload_from_bytes(storage_key, file_bytes)
                migrated_count += 1
                if migrated_count % 50 == 0:
                    logger.info(f"Migration progress: {migrated_count} files migrated")
            except Exception as e:
                logger.warning(f"Error migrating {file_path}: {e}")

    logger.info(f"Migration complete: {migrated_count} files migrated to cloud")
    return migrated_count
